"""Credential-free checks for tools/propagate.py on disposable git repositories."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools/propagate.py'

ALIGNMENT = """SHARED_DIRECTORIES = ('network', 'setup')
SHARED_TESTS = ('tests/test_alignment.py', 'tests/test_shared.py'{extra})
"""
# Same structure as a wrapper's tests/test_reference_copy.py.
MANIFEST_HEAD = '''"""Per-agent check that the shared components equal the Claude reference copy.

The shared files must stay byte-identical to ``claude-container`` at the tag.
"""
import hashlib
REFERENCE_TAG = '{tag}'
REFERENCE_COMMIT = '{commit}'
SIBLING = ROOT.parent / 'claude-container'
CLOSED_DIRECTORIES = ('network', 'setup')
SKIPPED_PARTS = ('__pycache__', 'bin')
MANIFEST = {{
{entries}}}


def differences(root):
    return []


def skip():
    return 'no sibling claude-container checkout'
'''
# Same structure as a wrapper's docs/network-contract.md: the reference line, a
# prose line naming the tag as history, and the parity table, whose target row
# is the profile's display_name (Pi).
CONTRACT = """The shared components come from `sandbox-container` at tag
`{tag}` (commit `{commit}`).

The guard fix arrived in `{tag}`, as recorded below.

| Wrapper | Contract adoption | Implementation | Real enforcement | Auth compatibility |
| --- | --- | --- | --- | --- |
| Sandbox (reference) | Reference (`{tag}`, shared core) | Guard integrated | WSL: `{tag}` modes passed (2026-11-01) | Not applicable |
| Codex | Adopted `{tag}`: shared core | Guard integrated | WSL: all modes passed on `{tag}` (2026-11-02) | Pending |
| Pi | Adopted `{tag}`: shared core | Guard integrated | WSL: all modes passed on `{tag}` (2026-11-03) | Pending |

Commit `{commit}` is the copied state.
"""
# A runner like Claude's: [[ ... ]] conditions, no --shared mode.
CLAUDE_RUNNER = """if [[ "${1:-}" == --wrapper ]]; then
    pattern=w
elif [[ "${1:-}" == --setup ]]; then
    pattern=s
elif [[ "${1:-}" == --setup-runtime ]]; then
    pattern=sr
elif [[ "${1:-}" == --qualification ]]; then
    pattern=q
elif [[ "${1:-}" == --network ]]; then
    pattern=n
elif [[ "${1:-}" == --guard || "${1:-}" == --guard-idle ]]; then
    pattern=g
fi
"""
PROFILE_WITH_IMAGES = ('{"name": "pi-container", "display_name": "Pi", '
                       '"images": {"agent": "localhost/pi", "toolchain": "localhost/pi-guard-toolchain"}}\n')
ENGINE_TESTS = {'tests/test_runtime.py': 'class SessionEngineTests(unittest.TestCase):\n    pass\n',
                'tests/test_network_runtime.py': ('class NetworkRuntime:\n'
                                                  '    def test_offline_session_engine_has_no_external_path(self):\n'
                                                  '        pass\n')}
RUNNER = """case "${1:-}" in
    --wrapper) pattern=test_wrapper.py ;;
    --shared) pattern='' ;;
    --setup) pattern=test_setup.py ;;
    --guard|--guard-idle) pattern=test_guard.py ;;
    --network) pattern=test_network_runtime.py ;;
esac
"""


def load_tool():
    import importlib.util
    spec = importlib.util.spec_from_file_location('propagate_tool', TOOL)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    return tool


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True).stdout


def write(root, files):
    for name, text in files.items():
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


class Propagation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='propagate-')
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.reference = base / 'reference'
        self.target = base / 'target'
        for repo in (self.reference, self.target):
            repo.mkdir()
            git(repo, 'init', '-q', '-b', 'main')
            git(repo, 'config', 'user.email', 'test@example.invalid')
            git(repo, 'config', 'user.name', 'Test')
        old = {'network/a.py': 'a = 1\n', 'network/b.py': 'b = 1\n', 'network/gone.py': 'gone\n',
               'setup/diagnostics.py': 'diagnostics = 1\n', 'setup/common.py': 'common = 1\n',
               'tests/test_alignment.py': ALIGNMENT.format(extra=''), 'tests/test_shared.py': 'shared = 1\n',
               'tests/test_reference_only.py': 'not shared\n'}
        self.old_files = old
        self.commit_tag(old, 'sandbox-ref-1')
        new = dict(old, **{'network/a.py': 'a = 2\n', 'network/c.py': 'c = 1\n', 'setup/common.py': 'common = 2\n',
                           'tests/test_alignment.py': ALIGNMENT.format(extra=", 'tests/test_new.py'"),
                           'tests/test_new.py': 'new = 1\n', 'tests/test_reference_only.py': 'changed\n'})
        del new['network/gone.py']
        self.commit_tag(new, 'sandbox-ref-2')
        self.old_commit = git(self.reference, 'rev-parse', 'sandbox-ref-1^{commit}').strip()
        self.new_commit = git(self.reference, 'rev-parse', 'sandbox-ref-2^{commit}').strip()
        # Target adopts network/ and the shared tests, but only setup/diagnostics.py.
        adopted = {name: old[name] for name in ('network/a.py', 'network/b.py', 'network/gone.py',
                                                 'setup/diagnostics.py', 'tests/test_alignment.py', 'tests/test_shared.py')}
        write(self.target, adopted)
        write(self.target, {
            'tests/test_reference_copy.py': self.manifest('sandbox-ref-1', self.old_commit, adopted),
            'tests/run-runtime.sh': RUNNER,
            'README.md': 'Copied from tag `sandbox-ref-1`; see sandbox-ref-10 and sandbox-ref-1x.\n',
            'agent/profile.json': '{"name": "pi-container", "display_name": "Pi"}\n',
            'docs/network-contract.md': CONTRACT.format(tag='sandbox-ref-1', commit=self.old_commit),
            'docs/validation.md': 'Adoption of `sandbox-ref-1`.\n',
            'CHANGELOG.md': 'Shared files now come from `sandbox-ref-1`.\n',
            'openspec/changes/archive/x/design.md': 'Copy from `sandbox-ref-1`.\n'})
        git(self.target, 'add', '-A')
        git(self.target, 'commit', '-q', '-m', 'adopt ref-1')

    def commit_tag(self, files, tag):
        for path in list(self.reference.rglob('*')):
            if path.is_file() and '.git' not in path.parts:
                path.unlink()
        write(self.reference, files)
        git(self.reference, 'add', '-A')
        git(self.reference, 'commit', '-q', '-m', tag)
        git(self.reference, 'tag', '-a', tag, '-m', tag)

    @staticmethod
    def manifest(tag, commit, files):
        entries = ''.join(f"    '{name}': '{hashlib.sha256(text.encode()).hexdigest()}',\n"
                          for name, text in sorted(files.items()))
        return MANIFEST_HEAD.format(tag=tag, commit=commit, entries=entries)

    def run_tool(self, *args, old='sandbox-ref-1', new='sandbox-ref-2'):
        return subprocess.run([sys.executable, '-I', str(TOOL), str(self.target), old, new,
                               '--reference', str(self.reference), *args], capture_output=True, text=True)

    def snapshot(self):
        return {p.relative_to(self.target): p.read_bytes() for p in self.target.rglob('*')
                if p.is_file() and '.git' not in p.parts}

    def test_manifest_is_pointed_at_the_reference(self):
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('manifest: names reference instead of claude-container', result.stdout)
        self.assertIn('claude-container', (self.target / 'tests/test_reference_copy.py').read_text())
        result = self.run_tool('--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        text = (self.target / 'tests/test_reference_copy.py').read_text()
        self.assertNotIn('claude-container', text)
        self.assertNotIn('Claude', text)
        self.assertIn("SIBLING = ROOT.parent / 'reference'", text)
        self.assertIn('equal the reference reference copy.', text)
        self.assertIn('byte-identical to ``reference`` at the tag', text)
        self.assertIn("'no sibling reference checkout'", text)

    def test_manifest_already_naming_the_reference_is_kept(self):
        path = self.target / 'tests/test_reference_copy.py'
        path.write_text(path.read_text().replace('claude-container', 'reference'))
        git(self.target, 'commit', '-q', '-am', 'name reference')
        before = path.read_text()
        result = self.run_tool('--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('manifest: names', result.stdout)
        after = path.read_text()
        self.assertEqual(after.replace('sandbox-ref-2', 'sandbox-ref-1').replace(self.new_commit, self.old_commit)
                         .split('MANIFEST = {')[0], before.split('MANIFEST = {')[0])

    def test_manifest_without_sibling_is_refused(self):
        path = self.target / 'tests/test_reference_copy.py'
        path.write_text(path.read_text().replace("SIBLING = ROOT.parent / 'claude-container'\n", ''))
        git(self.target, 'commit', '-q', '-am', 'drop sibling')
        before = self.snapshot()
        result = self.run_tool('--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SIBLING', result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_new_shared_directory_is_adopted_with_the_tag(self):
        current = {p.relative_to(self.reference).as_posix(): p.read_text()
                   for p in self.reference.rglob('*') if p.is_file() and '.git' not in p.parts}
        newer = dict(current, **{'launcher/core.sh': 'core = 1\n', 'tests/test_alignment.py': ALIGNMENT.format(
            extra=", 'tests/test_new.py'").replace("('network', 'setup')", "('network', 'setup', 'launcher')")})
        self.commit_tag(newer, 'sandbox-ref-3')
        result = self.run_tool(new='sandbox-ref-3')
        self.assertEqual(result.returncode, 0, result.stderr)
        added = next(line for line in result.stdout.splitlines() if line.startswith('added:'))
        self.assertIn('launcher/core.sh', added)
        self.assertNotIn('launcher/core.sh', next(line for line in result.stdout.splitlines()
                                                  if line.startswith('not adopted:')))

    def test_dry_run_plans_without_writing(self):
        before = self.snapshot()
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('modified: network/a.py, tests/test_alignment.py\n', result.stdout)
        self.assertIn('added: network/c.py, tests/test_new.py\n', result.stdout)
        self.assertIn('removed: network/gone.py\n', result.stdout)
        self.assertIn('not adopted: setup/common.py\n', result.stdout)
        # The contract: the tag and the commit of the reference line, the Pi and
        # reference adoption cells, and the last commit; five history mentions stay.
        self.assertIn('documents: README.md (1), docs/network-contract.md (5, 5 kept)\n', result.stdout)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(git(self.target, 'branch', '--show-current').strip(), 'main')

    def test_apply_copies_rewrites_and_keeps_history(self):
        result = self.run_tool('--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(git(self.target, 'branch', '--show-current').strip(), 'adopt-sandbox-ref-2')
        for name in ('network/a.py', 'network/c.py', 'tests/test_new.py', 'tests/test_alignment.py'):
            expected = git(self.reference, 'show', f'sandbox-ref-2:{name}')
            self.assertEqual((self.target / name).read_text(), expected, name)
        self.assertFalse((self.target / 'network/gone.py').exists())
        self.assertFalse((self.target / 'setup/common.py').exists())
        manifest = (self.target / 'tests/test_reference_copy.py').read_text()
        self.assertIn("REFERENCE_TAG = 'sandbox-ref-2'", manifest)
        self.assertIn(f"REFERENCE_COMMIT = '{self.new_commit}'", manifest)
        self.assertNotIn('network/gone.py', manifest)
        for name in ('network/a.py', 'network/b.py', 'network/c.py', 'setup/diagnostics.py', 'tests/test_new.py'):
            digest = hashlib.sha256((self.target / name).read_bytes()).hexdigest()
            self.assertIn(f"    '{name}': '{digest}',\n", manifest)
        self.assertTrue(manifest.endswith("def skip():\n    return 'no sibling reference checkout'\n"))
        readme = (self.target / 'README.md').read_text()
        self.assertEqual(readme, 'Copied from tag `sandbox-ref-2`; see sandbox-ref-10 and sandbox-ref-1x.\n')
        self.assertEqual((self.target / 'docs/network-contract.md').read_text(), self.adopted_contract())
        for name in ('docs/validation.md', 'CHANGELOG.md', 'openspec/changes/archive/x/design.md'):
            self.assertIn('sandbox-ref-1`', (self.target / name).read_text(), name)
        # No version-control side effects beyond the branch.
        self.assertEqual(git(self.target, 'log', '--oneline').count('\n'), 1)
        self.assertTrue(git(self.target, 'status', '--porcelain').strip())

    def adopted_contract(self):
        """The fixture contract after adopting sandbox-ref-2: only its current references moved."""
        return (CONTRACT.format(tag='sandbox-ref-1', commit=self.old_commit)
                .replace('`sandbox-ref-1` (commit', '`sandbox-ref-2` (commit')
                .replace('| Reference (`sandbox-ref-1`,', '| Reference (`sandbox-ref-2`,')
                .replace('| Pi | Adopted `sandbox-ref-1`:', '| Pi | Adopted `sandbox-ref-2`:')
                .replace(self.old_commit, self.new_commit))

    def test_contract_keeps_parity_history_and_other_rows(self):
        result = self.run_tool('--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = (self.target / 'docs/network-contract.md').read_text().splitlines()
        self.assertIn('The guard fix arrived in `sandbox-ref-1`, as recorded below.', lines)
        rows = {line.split(' | ')[0][2:]: line.split(' | ') for line in lines if line.startswith('| ')}
        # Real enforcement cells name the tag each result ran at.
        for label in ('Sandbox (reference)', 'Codex', 'Pi'):
            self.assertIn('`sandbox-ref-1`', rows[label][3], label)
        # Another wrapper holding the same tag keeps its adoption.
        self.assertEqual(rows['Codex'][1], 'Adopted `sandbox-ref-1`: shared core')
        self.assertEqual(rows['Pi'][1], 'Adopted `sandbox-ref-2`: shared core')
        self.assertEqual(rows['Sandbox (reference)'][1], 'Reference (`sandbox-ref-2`, shared core)')

    def test_contract_without_parity_table_moves_its_reference_line(self):
        contract = self.target / 'docs/network-contract.md'
        contract.write_text(CONTRACT.format(tag='sandbox-ref-1', commit=self.old_commit).split('| Wrapper')[0])
        (self.target / 'agent/profile.json').unlink()
        git(self.target, 'commit', '-qam', 'no parity table')
        result = self.run_tool('--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('docs/network-contract.md (2, 1 kept)\n', result.stdout)
        text = contract.read_text()
        self.assertIn(f'`sandbox-ref-2` (commit `{self.new_commit}`)', text)
        self.assertIn('The guard fix arrived in `sandbox-ref-1`', text)

    def test_contract_that_names_no_target_row_is_refused(self):
        contract = self.target / 'docs/network-contract.md'
        profile = self.target / 'agent/profile.json'
        pi_row = next(line for line in contract.read_text().splitlines(keepends=True) if line.startswith('| Pi |'))
        cases = (
            ('cannot read agent/profile.json', lambda: profile.unlink()),
            ('has no display_name', lambda: profile.write_text('{"name": "pi-container"}\n')),
            ("has 0 parity rows for 'Pi'", lambda: contract.write_text(contract.read_text().replace('| Pi |', '| Py |'))),
            ("has 2 parity rows for 'Pi'", lambda: contract.write_text(contract.read_text().replace(pi_row, pi_row * 2))),
            ('a parity row needs the 5 cells', lambda: contract.write_text(
                contract.read_text().replace('| Codex | Adopted', '| Codex | x | Adopted'))))
        for message, edit in cases:
            with self.subTest(message=message):
                edit()
                git(self.target, 'add', '-A')
                git(self.target, 'commit', '-qm', 'break the parity row')
                before = self.snapshot()
                for args in ((), ('--apply',)):
                    result = self.run_tool(*args)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn(message, result.stderr)
                    self.assertEqual(self.snapshot(), before)
                    self.assertEqual(git(self.target, 'branch', '--show-current').strip(), 'main')
                git(self.target, 'reset', '-q', '--hard', 'HEAD~1')

    def test_checklist_follows_the_changed_files_and_runner(self):
        result = self.run_tool()
        line = next(l for l in result.stdout.splitlines() if l.startswith('Run in the session: '))
        self.assertEqual(line, 'Run in the session: bash tests/run-runtime.sh --shared')
        self.assertIn('## Adoption of `sandbox-ref-2`:', result.stdout)
        self.assertIn('Adopt sandbox-ref-2', result.stdout)
        # A setup change selects the setup modes the runner offers; guard sources the guard/network modes.
        new = {'network/a.py': 'a = 2\n', 'network/b.py': 'b = 1\n', 'network/c.py': 'c = 1\n',
               'network/proxy.py': 'proxy\n', 'setup/diagnostics.py': 'diagnostics = 2\n',
               'setup/common.py': 'common = 2\n',
               'tests/test_alignment.py': ALIGNMENT.format(extra=", 'tests/test_new.py'"),
               'tests/test_shared.py': 'shared = 1\n', 'tests/test_new.py': 'new = 1\n',
               'tests/test_reference_only.py': 'changed\n'}
        self.commit_tag(new, 'sandbox-ref-3')
        result = self.run_tool(new='sandbox-ref-3')
        self.assertEqual(result.returncode, 0, result.stderr)
        line = next(l for l in result.stdout.splitlines() if l.startswith('Run in the session: '))
        self.assertEqual(line, 'Run in the session: bash tests/run-runtime.sh --shared; bash tests/run-runtime.sh --setup; '
                               'bash tests/run-runtime.sh --guard; bash tests/run-runtime.sh --network')

    def test_runner_modes_in_if_conditions(self):
        # Claude's runner tests modes in [[ ... ]] conditions, two of them joined by ||.
        tool = load_tool()
        runner = self.target / 'tests/run-runtime.sh'
        runner.write_text('if [[ "${1:-}" == --wrapper ]]; then\n    pattern=w\n'
                          'elif [[ "${1:-}" == --setup ]]; then\n    pattern=s\n'
                          'elif [[ "${1:-}" == --guard || "${1:-}" == --guard-idle ]]; then\n    pattern=g\nfi\n')
        self.assertEqual(tool.runner_modes(self.target), {'--wrapper', '--setup', '--guard', '--guard-idle'})
        self.assertEqual(tool.checklist(self.target, ['network/guard.c']), [
            tool.Entry('unit', 'unit', 'python3 -m unittest tests.test_reference_copy tests.test_alignment'),
            tool.Entry('mode', 'guard', 'bash tests/run-runtime.sh --guard')])

    def claude_like(self, files=None):
        """The fixture target with Claude's runner shape, a profile naming images, and extra test files."""
        write(self.target, dict({'tests/run-runtime.sh': CLAUDE_RUNNER, 'agent/profile.json': PROFILE_WITH_IMAGES},
                                **(files or {})))
        return load_tool()

    def names(self, entries):
        return [entry.name for entry in entries if entry.kind in ('unit', 'mode')]

    def test_launcher_core_selects_wrapper_and_default_runtime(self):
        tool = self.claude_like()
        entries = tool.checklist(self.target, ['launcher/core.sh'])
        self.assertEqual(self.names(entries), ['unit', 'wrapper', 'runtime'])
        self.assertIn(tool.Entry('mode', 'runtime', 'bash tests/run-runtime.sh'), entries)
        self.assertNotIn('prepare', [entry.kind for entry in entries])

    def test_engine_inputs_select_the_engine_cases(self):
        tool = self.claude_like(ENGINE_TESTS)
        for changed in (['setup/engine.py'], ['launcher/engine/start.sh']):
            with self.subTest(changed=changed):
                entries = tool.checklist(self.target, changed)
                self.assertIn(tool.Entry('prepare', 'engine', 'podman build --pull=never --tag '
                                         'localhost/pi-engine:latest launcher/engine'), entries)
                self.assertIn(tool.Entry('mode', 'runtime-engine', 'bash tests/run-runtime.sh -k SessionEngineTests'),
                              entries)
                self.assertIn(tool.Entry('mode', 'network-engine', 'bash tests/run-runtime.sh --network '
                                         '-k test_offline_session_engine_has_no_external_path'), entries)
                self.assertNotIn('runtime', self.names(entries))
                self.assertNotIn('network', self.names(entries))

    def test_engine_inputs_without_the_cases_select_the_full_modes(self):
        tool = self.claude_like()
        entries = tool.checklist(self.target, ['launcher/engine/Containerfile'])
        self.assertIn('runtime', self.names(entries))
        self.assertIn('network', self.names(entries))
        self.assertFalse({'runtime-engine', 'network-engine'} & set(self.names(entries)))

    def test_full_mode_drops_its_selection(self):
        tool = self.claude_like(ENGINE_TESTS)
        entries = tool.checklist(self.target, ['launcher/core.sh', 'launcher/engine/start.sh'])
        self.assertEqual(self.names(entries), ['unit', 'wrapper', 'runtime', 'network-engine'])
        self.assertEqual(len(entries), len(set(entries)))

    def test_qualified_file_selects_qualification(self):
        tool = self.claude_like()
        self.assertEqual(self.names(tool.checklist(self.target, ['network/a.py'])), ['unit'])
        self.assertIn('qualification', self.names(tool.checklist(self.target, ['network/a.py'], ('network/a.py',))))
        # SHARED_CODE is read from the tag; computed entries (the built guard, the profile) are not copied files.
        current = {path.relative_to(self.reference).as_posix(): path.read_text()
                   for path in self.reference.rglob('*') if path.is_file() and '.git' not in path.parts}
        self.commit_tag(dict(current, **{'network/qualification_records.py': (
            "GUARD = 'guard'\nSHARED_CODE = ('network/a.py', 'network/bin/' + GUARD, 'setup/engine.py')\n")}),
            'sandbox-ref-3')
        tool.REFERENCE = self.reference
        self.assertEqual(tool.qualified_code('sandbox-ref-3'), ('network/a.py', 'setup/engine.py'))
        self.assertEqual(tool.qualified_code('sandbox-ref-1'), ())

    def test_shared_test_modules_join_their_mode_or_the_unit_tests(self):
        tool = self.claude_like()
        entries = tool.checklist(self.target, ['tests/test_engine.py', 'tests/test_toolchains.py', 'tests/test_setup.py'])
        self.assertEqual(entries[-3:], [
            tool.Entry('unit', 'unit', 'python3 -m unittest tests.test_reference_copy tests.test_alignment '
                       'tests.test_engine tests.test_toolchains'),
            tool.Entry('mode', 'setup', 'bash tests/run-runtime.sh --setup'),
            tool.Entry('mode', 'setup-runtime', 'bash tests/run-runtime.sh --setup-runtime')])
        # A module whose mode the runner does not offer runs as a host unit test.
        entries = tool.checklist(self.target, ['tests/test_mux.py'])
        self.assertIn('tests.test_mux', next(entry.command for entry in entries if entry.kind == 'unit'))

    def test_helper_selects_the_modules_that_name_it(self):
        tool = self.claude_like({'tests/test_launcher.py': "FAKE = (TESTS / 'fake_podman.py').read_text()\n",
                                 'tests/test_other.py': 'fake_podman_like = 1\n'})
        entries = tool.checklist(self.target, ['tests/fake_podman.py'])
        self.assertEqual(self.names(entries), ['unit', 'wrapper'])
        self.assertNotIn('test_other', entries[-2].command)

    def test_windows_files_add_a_manual_step(self):
        tool = self.claude_like()
        for changed in (['launcher/windows/core.ps1'], ['sandbox-container.ps1']):
            with self.subTest(changed=changed):
                manual = [entry for entry in tool.checklist(self.target, changed) if entry.kind == 'manual']
                self.assertEqual(len(manual), 1)
                self.assertIn('windows-validate.ps1', manual[0].command)

    def test_images_follow_the_selected_modes(self):
        tool = self.claude_like()
        images = [entry.command for entry in tool.checklist(self.target, ['network/a.py']) if entry.kind == 'image']
        self.assertEqual(images, ['localhost/pi:latest'])
        images = [entry.command for entry in tool.checklist(self.target, ['network/proxy.py']) if entry.kind == 'image']
        self.assertEqual(images, ['localhost/pi:latest', 'localhost/pi-guard-toolchain:development'])
        (self.target / 'agent/profile.json').write_text('{"name": "pi-container", "display_name": "Pi"}\n')
        self.assertFalse([entry for entry in tool.checklist(self.target, ['network/proxy.py']) if entry.kind == 'image'])
        with self.assertRaisesRegex(tool.PropagationError, 'names no images.agent'):
            tool.checklist(self.target, ['setup/engine.py'])

    def test_report_prints_commands_with_private_storage(self):
        write(self.target, {'tests/run-runtime.sh': CLAUDE_RUNNER})
        git(self.target, 'commit', '-qam', 'claude runner')
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        line = next(l for l in result.stdout.splitlines() if l.startswith('Run in the session: '))
        self.assertEqual(line, 'Run in the session: SANDBOX_TEST_TMPDIR=<private directory> python3 -m unittest '
                               'tests.test_reference_copy tests.test_alignment tests.test_new')
        self.assertIn('Follow-up after closure:\n- on WSL or the native Linux host, from sandbox-container: '
                      f'bash tools/adoption-run.sh {self.target.resolve()} sandbox-ref-1 sandbox-ref-2\n', result.stdout)
        self.assertIn('| `SANDBOX_TEST_TMPDIR=<private directory> python3 -m unittest tests.test_reference_copy '
                      'tests.test_alignment tests.test_new` | <fill in> |', result.stdout)

    def windows_tag(self):
        """Tag sandbox-ref-3, which adds the Windows shim in the new shared directory launcher/."""
        current = {p.relative_to(self.reference).as_posix(): p.read_text()
                   for p in self.reference.rglob('*') if p.is_file() and '.git' not in p.parts}
        newer = dict(current, **{'launcher/windows/core.ps1': 'shim\n', 'tests/test_alignment.py': ALIGNMENT.format(
            extra=", 'tests/test_new.py'").replace("('network', 'setup')", "('network', 'setup', 'launcher')")})
        self.commit_tag(newer, 'sandbox-ref-3')
        return load_tool()

    def test_report_lists_the_follow_up_after_closure(self):
        tool = self.windows_tag()
        result = self.run_tool(new='sandbox-ref-3')
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        runner = ('on WSL or the native Linux host, from sandbox-container: bash tools/adoption-run.sh '
                  f'{self.target.resolve()} sandbox-ref-1 sandbox-ref-3')
        start = lines.index('Follow-up after closure:')
        self.assertEqual(lines[start + 1:start + 3], ['- ' + runner, '- ' + tool.WINDOWS_STEP])
        template = lines[lines.index('Validation record template (docs/validation.md):'):]
        rows = [line for line in template if line.startswith('| `')]
        self.assertTrue(rows)
        self.assertFalse([row for row in rows if 'windows-validate' in row or 'adoption-run' in row])
        self.assertIn('- ' + runner + ': pending', template)
        self.assertIn('- ' + tool.WINDOWS_STEP + ': pending', template)
        self.assertFalse([line for line in lines if line.startswith(('Manual:', 'On one host'))])

    def test_follow_up_block_is_plain_bullets(self):
        self.windows_tag()
        lines = self.run_tool(new='sandbox-ref-3').stdout.splitlines()
        start = lines.index('Follow-up after closure:')
        block = lines[start + 1:lines.index('', start)]
        self.assertEqual(len(block), 2)
        for line in block:
            self.assertTrue(line.startswith('- ') and not line.startswith('- ['), line)
        self.assertFalse([line for line in lines if '[ ]' in line])

    def test_checklist_keeps_manual_steps_for_the_runner(self):
        tool = self.windows_tag()
        self.assertEqual(self.run_tool('--apply', new='sandbox-ref-3').returncode, 0)
        result = self.run_tool('--checklist', new='sandbox-ref-3')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(['manual', 'windows', tool.WINDOWS_STEP],
                      [line.split('\t') for line in result.stdout.splitlines()])

    def test_checklist_of_an_adopted_target(self):
        result = self.run_tool('--checklist')
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('adopts sandbox-ref-1', result.stderr)
        self.assertEqual(result.stdout, '')
        self.assertEqual(self.run_tool('--apply').returncode, 0)
        (self.target / 'README.md').write_text('local edit\n')
        before = self.snapshot()
        result = self.run_tool('--checklist')
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [line.split('\t') for line in result.stdout.splitlines()]
        self.assertTrue(lines)
        for fields in lines:
            self.assertEqual(len(fields), 3, fields)
            self.assertIn(fields[0], ('unit', 'mode', 'prepare', 'image', 'manual'))
        self.assertEqual(lines[0], ['mode', 'shared', 'bash tests/run-runtime.sh --shared'])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(git(self.target, 'branch', '--show-current').strip(), 'adopt-sandbox-ref-2')
        self.assertEqual(self.run_tool('--checklist', '--apply').returncode, 2)

    def test_preconditions_refuse_without_writing(self):
        cases = []
        (self.target / 'README.md').write_text('local edit\n')
        cases.append(('uncommitted changes', {}))
        for message, kwargs in cases:
            before = self.snapshot()
            result = self.run_tool(**kwargs)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)
            self.assertEqual(self.snapshot(), before)
        git(self.target, 'checkout', '--', 'README.md')
        for kwargs, message in (({'old': 'sandbox-ref-2', 'new': 'sandbox-ref-2'}, 'adopts sandbox-ref-1'),
                                ({'new': 'sandbox-ref-9'}, 'tag sandbox-ref-9 does not exist')):
            result = self.run_tool(**kwargs)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn(message, result.stderr)
        # A forked shared file is refused.
        (self.target / 'network/b.py').write_text('b = 99\n')
        git(self.target, 'commit', '-qam', 'fork')
        result = self.run_tool()
        self.assertEqual(result.returncode, 1)
        self.assertIn('network/b.py differs from sandbox-ref-1', result.stderr)
        git(self.target, 'reset', '-q', '--hard', 'HEAD~1')
        # An existing adoption branch is refused.
        git(self.target, 'branch', 'adopt-sandbox-ref-2')
        result = self.run_tool('--apply')
        self.assertEqual(result.returncode, 1)
        self.assertIn('branch adopt-sandbox-ref-2 already exists', result.stderr)
        self.assertEqual(git(self.target, 'branch', '--show-current').strip(), 'main')
        git(self.target, 'branch', '-D', 'adopt-sandbox-ref-2')
        # A malformed manifest is refused.
        manifest = self.target / 'tests/test_reference_copy.py'
        manifest.write_text(manifest.read_text().replace("',\n}", "'\n}"))
        git(self.target, 'commit', '-qam', 'malformed')
        result = self.run_tool()
        self.assertEqual(result.returncode, 1)
        self.assertIn('unreadable manifest line', result.stderr)

    def test_same_tag_reports_no_changes(self):
        result = self.run_tool(old='sandbox-ref-1', new='sandbox-ref-1')
        self.assertEqual(result.returncode, 0, result.stderr)
        for label in ('modified', 'added', 'removed', 'not adopted', 'documents', 'reference changes'):
            self.assertIn(label + ': none\n', result.stdout)
        self.assertNotIn('review: ', result.stdout)

    def test_review_lists_own_lines_naming_a_changed_directory(self):
        # The range adds network/c.py and removes network/gone.py: a target line naming
        # a network file may belong to a hand-written list of that directory.
        listing = "for name in ('network/a.py', 'network/b.py'):\n    pass\n"
        write(self.target, {'tests/test_own.py': 'import os\n' + listing, 'docs/validation.md': listing,
                            'CHANGELOG.md': listing, 'openspec/changes/archive/x/design.md': listing,
                            'tests/test_reference_copy.py': (self.target / 'tests/test_reference_copy.py').read_text()
                            + '# network/a.py\n', 'notes/gone.txt': 'see network/gone.py\n'})
        git(self.target, 'add', '-A')
        git(self.target, 'commit', '-qm', 'own lists')
        for args in ((), ('--apply',)):
            with self.subTest(args=args):
                result = self.run_tool(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual([line for line in result.stdout.splitlines() if line.startswith('review: ')],
                                 ['review: notes/gone.txt:1', 'review: tests/test_own.py:2'])

    def test_review_is_silent_without_additions_or_removals(self):
        write(self.target, {'tests/test_own.py': "NAMES = ('network/a.py', 'network/b.py')\n"})
        git(self.target, 'add', '-A')
        git(self.target, 'commit', '-qm', 'own list')
        self.commit_tag(dict(self.old_files, **{'network/a.py': 'a = 3\n'}), 'sandbox-ref-3')
        result = self.run_tool(new='sandbox-ref-3')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('modified: network/a.py\n', result.stdout)
        self.assertNotIn('review: ', result.stdout)

    def test_reference_changes_of_the_range(self):
        write(self.reference, {'openspec/changes/alpha/specs/cap-a/spec.md': 'alpha\n',
                               'openspec/changes/beta/specs/reference-propagation/spec.md': 'beta\n',
                               'openspec/changes/gamma/proposal.md': 'gamma\n'})
        git(self.reference, 'add', '-A')
        git(self.reference, 'commit', '-qm', 'three changes')
        (self.reference / 'openspec/changes/archive').mkdir()
        git(self.reference, 'mv', 'openspec/changes/beta', 'openspec/changes/archive/2026-11-25-beta')
        git(self.reference, 'commit', '-qm', 'archive beta')
        git(self.reference, 'tag', '-a', 'sandbox-ref-3', '-m', 'sandbox-ref-3')
        # Archived after the tag: the plan reads the location at HEAD.
        git(self.reference, 'mv', 'openspec/changes/alpha', 'openspec/changes/archive/2026-11-26-alpha')
        git(self.reference, 'commit', '-qm', 'archive alpha')
        write(self.target, {'openspec/specs/cap-a/spec.md': 'cap-a\n'})
        git(self.target, 'add', '-A')
        git(self.target, 'commit', '-qm', 'cap-a')
        result = self.run_tool(new='sandbox-ref-3')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('reference changes: 3\n'
                      '  alpha: archive/2026-11-26-alpha; specs: cap-a\n'
                      '  beta: archive/2026-11-25-beta; specs: reference-propagation [not in target]\n'
                      '  gamma: active; specs: none\n', result.stdout)


if __name__ == '__main__':
    unittest.main()
