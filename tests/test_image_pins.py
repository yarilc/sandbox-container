"""Credential-free checks that the reference image inputs are pinned (B05)."""
import ast
import fnmatch
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ('@fission-ai/openspec',)
# The reference image is a shell: no agent CLI may be installed.
AGENT_CLIS = ('@anthropic-ai/claude-code', '@openai/codex', 'opencode-ai', '@mariozechner/pi-coding-agent')
VERSION = re.compile(r'\d+\.\d+\.\d+')


def pins(recipe):
    """Return (base reference, {ARG name: default}, installed package specifiers)."""
    lines = recipe.replace('\\\n', ' ').splitlines()
    bases = [line.split()[1] for line in lines if line.startswith('FROM ')]
    if len(bases) != 1:
        raise ValueError('expected exactly one FROM line')
    args = dict(re.findall(r'^ARG ([A-Z_]+)=(\S+)$', recipe, re.MULTILINE))
    installs = []
    for line in lines:
        if 'npm install' in line or 'npm i ' in line:
            for command in line.split('&&'):
                if 'npm install' not in command and 'npm i ' not in command:
                    continue
                for token in command.split():
                    token = token.strip('"\'')
                    if token.startswith('@') or (not token.startswith('-') and '/' not in token
                                                 and token not in ('npm', 'install', 'i')):
                        for name, value in args.items():
                            token = token.replace('${' + name + '}', value).replace('$' + name, value)
                        installs.append(token)
    return bases[0], args, installs


def violations(recipe):
    found = []
    base, args, installs = pins(recipe)
    if not re.fullmatch(r'[a-z0-9./:-]+@sha256:[a-f0-9]{64}', base):
        found.append('base image is not pinned by digest: ' + base)
    seen = {}
    for spec in installs:
        name, _, version = spec.rpartition('@')
        if not name:
            found.append('unpinned package: ' + spec)
            continue
        if not VERSION.fullmatch(version):
            found.append('package is not pinned to an exact version: ' + spec)
        seen[name] = version
    for package in PACKAGES:
        if package not in seen:
            found.append('required package is not installed with a pinned version: ' + package)
    for package in AGENT_CLIS:
        if package in seen or package in recipe:
            found.append('agent CLI installed in the reference image: ' + package)
    return found


SOURCES = '/etc/apt/sources.list.d/debian.sources'
BOOTSTRAP_CA = '/tmp/apt-bootstrap-ca.pem'
INSECURE_APT = re.compile(r'Verify-(?:Peer|Host)\s*[= ]\s*"?(?:false|no|0)\b'
                          r'|AllowInsecureRepositories|--allow-insecure|--allow-unauthenticated'
                          r'|trusted=yes|\[trusted', re.IGNORECASE)


def transport_violations(recipe):
    """Return package-source transport violations (Debian over verified HTTPS only)."""
    text = recipe.replace('\\\n', ' ')
    found = []
    if re.search(r'http://deb\.debian\.org', text):
        found.append('plain-HTTP Debian source: http://deb.debian.org')
    for match in INSECURE_APT.finditer(text):
        found.append('apt TLS or signature verification disabled: ' + match[0])
    rewrite = re.search(r"sed -i '?s\|\^URIs: http://\|URIs: https://\|'? " + re.escape(SOURCES), text)
    update = re.search(r'apt-get\b[^&]*\bupdate\b', text)
    if not rewrite:
        found.append('Debian sources are not rewritten to HTTPS')
    elif update and update.start() < rewrite.start():
        found.append('Debian sources are rewritten to HTTPS only after apt-get update')
    # Bootstrap trust comes only from the pinned base's Node roots and is removed in the same step.
    bootstrap = re.search(r'rootCertificates[^&]*>\s*' + re.escape(BOOTSTRAP_CA), text)
    if not bootstrap or (rewrite and bootstrap.start() > rewrite.start()):
        found.append('bootstrap CA bundle is not exported from the base Node roots before the rewrite')
    for command in re.findall(r'apt-get\b[^&]*', text):
        if re.search(r'\b(update|install)\b', command) and 'Acquire::https::CAInfo=' + BOOTSTRAP_CA not in command:
            found.append('apt-get fetch without the bootstrap CA: ' + command.split(' -y')[0].strip())
    # The optional host CA arrives only as a build secret, never as a copied file.
    if not re.search(r'RUN --mount=type=secret,id=build-ca,required=false\b', text):
        found.append('optional build-ca secret mount is missing')
    for match in re.finditer(r'(?im)^(?:COPY|ADD)\b[^\n]*(?:\.pem|\.crt|ca-?bundle|certs?\b)', text):
        found.append('CA material copied into the image: ' + match[0])
    if 'build-ca' in text and not re.search(r'cat /run/secrets/build-ca >> ' + re.escape(BOOTSTRAP_CA), text):
        found.append('build-ca secret is not appended to the bootstrap CA bundle')
    steps = [line for line in text.splitlines() if BOOTSTRAP_CA in line]
    if not steps or len(steps) != 1 or 'rm -f ' + BOOTSTRAP_CA not in steps[0]:
        found.append('bootstrap CA bundle is not removed in the step that creates it')
    return found


def workdir_violations(recipe):
    """WORKDIR must name a directory created by an earlier build step, never by the engine at start."""
    text = recipe.replace('\\\n', ' ')
    found = []
    for match in re.finditer(r'(?m)^WORKDIR\s+(\S+)\s*$', text):
        path = match[1]
        before = text[:match.start()]
        created = any(re.search(r'\bmkdir\s+(?:-\S+\s+)*(?:\S+\s+)*' + re.escape(path) + r'(?=\s|$)', step)
                      for step in re.findall(r'(?m)^RUN\b.*$', before))
        if not created:
            found.append('WORKDIR is not created by a build step: ' + path)
    return found


class ImagePinTests(unittest.TestCase):
    def setUp(self):
        self.recipe = (ROOT / 'Containerfile').read_text()

    def test_shipped_recipe_is_pinned_and_starts_bash(self):
        self.assertEqual(violations(self.recipe), [])
        _, args, installs = pins(self.recipe)
        self.assertEqual(installs, ['@fission-ai/openspec@' + args['OPENSPEC_VERSION']])
        self.assertIn('ENTRYPOINT ["bash"]', self.recipe)
        self.assertRegex(self.recipe, r'(?m)^\s+HOME=/sandbox-home$')

    def test_mutated_recipes_are_rejected(self):
        digest = re.search(r'@sha256:[a-f0-9]{64}', self.recipe)
        cases = {
            'tag-only base': self.recipe.replace(digest[0], '') if digest else self.recipe,
            'latest package': self.recipe.replace('"@fission-ai/openspec@${OPENSPEC_VERSION}"',
                                                  '@fission-ai/openspec@latest'),
            'unversioned package': self.recipe.replace('"@fission-ai/openspec@${OPENSPEC_VERSION}"',
                                                       '@fission-ai/openspec'),
            'version range': self.recipe.replace('ARG OPENSPEC_VERSION=2.0.0', 'ARG OPENSPEC_VERSION=^2.0.0'),
            'agent cli': self.recipe.replace('"@fission-ai/openspec@${OPENSPEC_VERSION}"',
                                             '"@fission-ai/openspec@${OPENSPEC_VERSION}" @anthropic-ai/claude-code@2.1.316'),
        }
        for name, recipe in cases.items():
            with self.subTest(name=name):
                self.assertNotEqual(recipe, self.recipe)
                self.assertTrue(violations(recipe))
        message = violations(cases['agent cli'])
        self.assertTrue(any('agent CLI' in item for item in message), message)


    def test_workdir_exists_in_the_image(self):
        self.assertEqual(workdir_violations(self.recipe), [])
        self.assertIn('WORKDIR /workspace', self.recipe)
        mutated = self.recipe.replace('mkdir -p /sandbox-home /workspace', 'mkdir -p /sandbox-home')
        self.assertNotEqual(mutated, self.recipe)
        self.assertEqual(workdir_violations(mutated), ['WORKDIR is not created by a build step: /workspace'])
        self.assertTrue(workdir_violations('FROM x@sha256:' + 'a' * 64 + '\nRUN mkdir -p /other\nWORKDIR /workspace\n'))

    def test_package_sources_use_verified_https(self):
        self.assertEqual(transport_violations(self.recipe), [])

    def test_insecure_transport_recipes_are_rejected(self):
        rewrite = "sed -i 's|^URIs: http://|URIs: https://|' " + SOURCES
        option = '-o Acquire::https::CAInfo=' + BOOTSTRAP_CA
        cases = {
            'plain http restored': self.recipe.replace(rewrite, 'true'),
            'peer verification disabled': self.recipe.replace(option, option + ' -o Acquire::https::Verify-Peer=false', 1),
            'host verification disabled': self.recipe.replace(option, option + ' -o Acquire::https::Verify-Host=false', 1),
            'insecure repositories': self.recipe.replace(option, option + ' -o Acquire::AllowInsecureRepositories=true', 1),
            'rewrite after update': self.recipe.replace('    && ' + rewrite + ' \\\n', '').replace(
                '    && npm install', '    && ' + rewrite + ' \\\n    && npm install', 1),
            'literal http source': self.recipe.replace(rewrite, rewrite + ' && echo http://deb.debian.org/debian'),
            'fetch without bootstrap ca': self.recipe.replace(option + ' update', 'update', 1),
            'bootstrap ca kept': self.recipe.replace('    && rm -f ' + BOOTSTRAP_CA + ' \\\n', ''),
            'secret mount required': self.recipe.replace('id=build-ca,required=false', 'id=build-ca,required=true'),
            'secret not appended': self.recipe.replace('cat /run/secrets/build-ca >> ', 'true ', 1),
            'bundle copied': self.recipe.replace('WORKDIR /workspace', 'COPY bundle.pem /etc/ssl/certs/host.pem\nWORKDIR /workspace'),
        }
        for name, recipe in cases.items():
            with self.subTest(name=name):
                self.assertNotEqual(recipe, self.recipe)
                self.assertTrue(transport_violations(recipe))


TOOLCHAIN_CA = '/tmp/apk-bootstrap-ca.pem'


def toolchain_violations(recipe):
    """The guard toolchain keeps exact pins and takes the host CA only as an optional build secret."""
    text = recipe.replace('\\\n', ' ')
    found = []
    if not re.search(r'(?m)^FROM docker\.io/library/alpine@sha256:[a-f0-9]{64}$', recipe):
        found.append('toolchain base is not pinned by digest')
    for package in re.findall(r'apk add --no-cache ([^&\n]+)', text):
        for spec in package.split():
            if not re.fullmatch(r'[a-z0-9-]+=[0-9][A-Za-z0-9._-]*', spec):
                found.append('toolchain package is not pinned: ' + spec)
    if not re.search(r'RUN --mount=type=secret,id=build-ca,required=false\b', text):
        found.append('optional build-ca secret mount is missing')
    if not re.search(r'SSL_CERT_FILE=' + re.escape(TOOLCHAIN_CA) + r' apk add\b', text):
        found.append('apk does not verify against the bootstrap bundle')
    if 'rm -f ' + TOOLCHAIN_CA not in text or len([l for l in text.splitlines() if TOOLCHAIN_CA in l]) != 1:
        found.append('toolchain bootstrap bundle is not removed in the step that creates it')
    if INSECURE_APT.search(text) or re.search(r'--allow-untrusted|--no-check-certificate|http://', text):
        found.append('toolchain fetch verification weakened')
    if re.search(r'(?im)^(?:COPY|ADD)\b', recipe):
        found.append('toolchain recipe copies host files')
    return found


class ToolchainRecipeTests(unittest.TestCase):
    def test_toolchain_recipe_is_pinned_and_takes_ca_only_as_secret(self):
        recipe = (ROOT / 'network/guard-build.Containerfile').read_text()
        self.assertEqual(toolchain_violations(recipe), [])
        cases = {
            'unpinned package': recipe.replace('gcc=13.2.1_git20240309-r1', 'gcc'),
            'required secret': recipe.replace('required=false', 'required=true'),
            'bundle kept': recipe.replace('    && rm -f ' + TOOLCHAIN_CA, '    && true'),
            'no bootstrap trust': recipe.replace('SSL_CERT_FILE=' + TOOLCHAIN_CA + ' ', ''),
            'untrusted packages': recipe.replace('apk add --no-cache', 'apk add --allow-untrusted --no-cache'),
            'copied bundle': recipe.replace('ENV LC_ALL', 'COPY bundle.pem /etc/ssl/certs/host.pem\nENV LC_ALL'),
        }
        for name, mutated in cases.items():
            with self.subTest(name=name):
                self.assertNotEqual(mutated, recipe)
                self.assertTrue(toolchain_violations(mutated))
        ignore = (ROOT / 'network/.containerignore').read_text().splitlines()
        self.assertIn('!podman-build-secret*', ignore)


SYSTEMD_SAMPLE = 'tests/systemd-sample.Containerfile'


def systemd_sample_violations(recipe):
    """What makes the systemd sample unrepeatable: an unpinned base, or any build step."""
    lines = [line for line in recipe.replace('\\\n', ' ').splitlines() if line.strip() and not line.startswith('#')]
    bases = [line.split()[1] for line in lines if line.startswith('FROM ')]
    found = []
    if len(bases) != 1 or not re.fullmatch(
            r'docker\.io/rockylinux/rockylinux:9-ubi-init@sha256:[a-f0-9]{64}', bases[0]):
        found.append("the base must be Rocky Linux 9's init image pinned by digest")
    for line in lines:
        if line.split()[0].upper() not in ('FROM', 'STOPSIGNAL', 'CMD', 'LABEL'):
            found.append('build step: ' + line)
    return found


class SystemdSampleRecipeTests(unittest.TestCase):
    # support-nested-systemd-containers, design D6: the fixture of the systemd cases.
    def test_systemd_sample_is_pinned_and_has_no_build_step(self):
        recipe = (ROOT / SYSTEMD_SAMPLE).read_text()
        self.assertEqual(systemd_sample_violations(recipe), [])
        base = re.search(r'(?m)^FROM (\S+)$', recipe).group(1)
        cases = {
            'tag only': recipe.replace(base, base.split('@')[0]),
            'other base': recipe.replace('rockylinux:9-ubi-init@', 'rockylinux:9-minimal@'),
            'package install': recipe + 'RUN dnf -y install systemd\n',
            'copied file': recipe + 'COPY unit.service /etc/systemd/system/\n',
            'second base': recipe + 'FROM docker.io/library/alpine@sha256:' + 'a' * 64 + '\n',
        }
        for name, mutated in cases.items():
            with self.subTest(name=name):
                self.assertNotEqual(mutated, recipe)
                self.assertTrue(systemd_sample_violations(mutated))


def copied_sources(recipe):
    """Return local source paths copied by COPY instructions (excluding --from stages)."""
    sources = []
    for raw in recipe.replace('\\\n', ' ').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        tokens = line.split()
        if tokens[0].upper() != 'COPY':
            continue
        flags = [tok for tok in tokens[1:] if tok.startswith('--')]
        if any(flag.startswith('--from=') for flag in flags):
            continue
        operands = [tok for tok in tokens[1:] if not tok.startswith('--')]
        if len(operands) >= 2:
            sources.extend(op.removeprefix('./').removeprefix('/') for op in operands[:-1])
    return sources


def _ignore_rule_matches(pattern, path):
    if pattern == '**':
        return True
    if pattern.endswith('/**'):
        prefix = pattern[:-3]
        return path.startswith(prefix + '/')
    return fnmatch.fnmatchcase(path, pattern)


def _ignore_path_admitted(rules, path):
    admitted = True
    for negated, pattern in rules:
        if _ignore_rule_matches(pattern, path):
            admitted = negated
    return admitted


def containerignore_admits(ignore_text, relative_path):
    """Evaluate a .containerignore allowlist for relative_path and its parent directories."""
    rules = []
    for raw in ignore_text.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        negated = line.startswith('!')
        pattern = (line[1:] if negated else line).removeprefix('./').removeprefix('/')
        rules.append((negated, pattern))
    parts = relative_path.strip('/').split('/')
    for depth in range(1, len(parts) + 1):
        candidate = '/'.join(parts[:depth])
        if not _ignore_path_admitted(rules, candidate):
            return False
    return True


def build_context_violations(context_dir, recipe_text=None, ignore_text=None):
    """Verify Containerfile COPY inputs exist and are admitted by the sibling .containerignore."""
    recipe_text = (context_dir / 'Containerfile').read_text() if recipe_text is None else recipe_text
    ignore_text = (context_dir / '.containerignore').read_text() if ignore_text is None else ignore_text
    found = []
    for meta in ('Containerfile', '.containerignore'):
        if not containerignore_admits(ignore_text, meta):
            found.append(f'build context excludes {meta}')
    for source in copied_sources(recipe_text):
        if not (context_dir / source).is_file():
            found.append(f'missing COPY source: {source}')
        elif not containerignore_admits(ignore_text, source):
            found.append(f'COPY source excluded by .containerignore: {source}')
    return found


def copied_python_import_violations(context_dir, recipe_text, module_dir):
    """Verify every local Python module imported by copied .py files is also copied into the image."""
    py_sources = [source for source in copied_sources(recipe_text) if source.endswith('.py')]
    copied_modules = {Path(source).stem for source in py_sources}
    local_modules = {path.stem for path in module_dir.glob('*.py')}
    found = []
    for source in py_sources:
        path = context_dir / source
        if not path.is_file():
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split('.')[0])
        for missing in sorted((imports & local_modules) - copied_modules):
            found.append(f'{source} imports uncopied local module {missing}')
    return found


class BuildContextTests(unittest.TestCase):
    def test_shipped_containerfiles_match_containerignore_and_local_imports(self):
        for relative in ('.', 'network', 'launcher/engine'):
            context_dir = ROOT if relative == '.' else ROOT / relative
            with self.subTest(context=relative):
                self.assertEqual(build_context_violations(context_dir), [])
        self.assertEqual(
            copied_python_import_violations(ROOT / 'network', (ROOT / 'network/Containerfile').read_text(), ROOT / 'network'),
            [],
        )
        self.assertEqual(
            copied_python_import_violations(ROOT, (ROOT / 'Containerfile').read_text(), ROOT / 'network'),
            [],
        )

    def test_missing_containerignore_entry_or_copied_import_is_detected(self):
        net_ignore = (ROOT / 'network/.containerignore').read_text()
        self.assertTrue(build_context_violations(ROOT / 'network', ignore_text=net_ignore.replace('!mirror.py\n', '')))

        root_ignore = (ROOT / '.containerignore').read_text()
        self.assertTrue(build_context_violations(ROOT, ignore_text=root_ignore.replace('!network/revisions.py\n', '')))
        self.assertTrue(build_context_violations(ROOT, ignore_text=root_ignore.replace('!network\n', '')))

        engine_ignore = (ROOT / 'launcher/engine/.containerignore').read_text()
        self.assertTrue(build_context_violations(ROOT / 'launcher/engine', ignore_text=engine_ignore.replace('!entrypoint.sh\n', '')))

        root_recipe = (ROOT / 'Containerfile').read_text()
        self.assertTrue(copied_python_import_violations(ROOT, root_recipe.replace(' network/revisions.py', ''), ROOT / 'network'))

        net_recipe = (ROOT / 'network/Containerfile').read_text()
        self.assertTrue(copied_python_import_violations(ROOT / 'network', net_recipe.replace(' mirror_metadata.py', ''), ROOT / 'network'))


if __name__ == '__main__':
    unittest.main()
