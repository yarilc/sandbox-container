#!/usr/bin/env python3
"""Propagate a new reference tag of the shared components to a wrapper checkout.

Usage: python3 -I tools/propagate.py <target> <old-tag> <new-tag> [--apply | --checklist]

Reference-only: this tool lives in sandbox-container and is never copied.
It reads the tags from this checkout, verifies that the target is a clean,
unforked adopter of <old-tag>, and prints (dry run) or applies the changes:
shared files, the tests/test_reference_copy.py manifest and the tag/commit
references in current-state documents. In docs/network-contract.md these are
the reference line and the contract adoption cells of the target's and the
reference's parity rows; the rest of the table is history. It never runs
suites, commits, merges, tags or pushes. See docs/propagation.md.

The plan also names the commands that validate the adoption, by changed
component, the target's own lines to review, and the reference's OpenSpec
changes of the range. --checklist prints those commands, one tab-separated
line each, for a target that has already adopted <new-tag>; tools/adoption-run.sh
runs them.
"""
import argparse
import ast
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

REFERENCE = Path(__file__).resolve().parents[1]
MANIFEST_FILE = 'tests/test_reference_copy.py'
ALIGNMENT_FILE = 'tests/test_alignment.py'
# Current-state documents; history (docs/validation.md, CHANGELOG.md, todo.md,
# openspec/) is never rewritten.
DOCUMENTS = ('README.md', 'AGENTS.md', 'CONTRIBUTING.md', 'docs/setup.md', 'docs/network-contract.md')
# In the network contract only the reference line and two parity cells are
# current state; the rest of the parity table records history.
CONTRACT = 'docs/network-contract.md'
PROFILE_FILE = 'agent/profile.json'
PARITY_HEADER = ['Wrapper', 'Contract adoption']
REFERENCE_ROW = ' (reference)'
SKIPPED_PARTS = ('__pycache__', 'bin')
TAG_LINE = re.compile(r"^REFERENCE_TAG = '([^']+)'$", re.M)
COMMIT_LINE = re.compile(r"^REFERENCE_COMMIT = '([0-9a-f]{40})'$", re.M)
ENTRY = re.compile(r"^    '([^']+)': '([0-9a-f]{64})',$")
# The reference checkout the manifest's sibling check compares against.
SIBLING_LINE = re.compile(r"^SIBLING = ROOT\.parent / '([^'/]+)'$", re.M)
COPY_LINE = re.compile(r'the [\w-]+ reference copy')
# The qualification gate digests the files of SHARED_CODE (docs/propagation.md).
QUALIFICATION_FILE = 'network/qualification_records.py'
RUNNER = 'tests/run-runtime.sh'
# The runner mode that runs each test module ('' is the default runtime mode).
# A changed shared module without an offered mode joins the host unit tests.
MODE_TESTS = {
    'tests/test_setup.py': '--setup', 'tests/test_setup_runtime.py': '--setup-runtime',
    'tests/test_qualification.py': '--qualification', 'tests/test_launcher.py': '--wrapper',
    'tests/test_wrapper.py': '--wrapper', 'tests/test_runtime.py': '',
    'tests/test_network_feasibility.py': '--network-feasibility', 'tests/test_network_policy.py': '--network-policy',
    'tests/test_mux.py': '--mux', 'tests/test_guard.py': '--guard', 'tests/test_network_runtime.py': '--network',
}
# The order in which the checklist names the runner modes.
MODE_ORDER = ('--setup', '--setup-runtime', '--qualification', '--wrapper', '', '--network-feasibility',
              '--network-policy', '--mux', '--guard', '--network')
ENGINE_INPUTS = ('launcher/engine/', 'setup/engine.py')
# The engine cases of the default and network runtime modes. Wrappers keep the
# reference's test names when they port them; a target without them runs the
# whole mode.
ENGINE_CASES = (
    ('', 'runtime-engine', 'tests/test_runtime.py', r'(?m)^class SessionEngineTests\b', '-k SessionEngineTests'),
    ('--network', 'network-engine', 'tests/test_network_runtime.py',
     r'(?m)^\s+def test_offline_session_engine_has_no_external_path\b',
     '-k test_offline_session_engine_has_no_external_path'),
)
WINDOWS_STEP = ('on a Windows host, from sandbox-container: .\\tools\\windows-validate.ps1 -Checkout <the Windows '
                'checkout>, on Windows PowerShell 5.1')
# Host unit tests need private, executable temporary storage: the toolchain
# library refuses a world-writable ancestor such as /tmp.
PRIVATE_STORAGE = 'SANDBOX_TEST_TMPDIR=<private directory> '
# Lines of the target that are history or planning, never checked for review.
REVIEW_EXCLUDED = ('docs/validation.md', 'CHANGELOG.md')
CHANGES = 'openspec/changes'

# One checklist line: kind is unit, mode, prepare, image or manual.
Entry = collections.namedtuple('Entry', 'kind name command')


class PropagationError(Exception):
    pass


def git(repo, *args, data=False):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True)
    if result.returncode:
        raise PropagationError('git ' + ' '.join(args) + ' failed: ' + result.stderr.decode(errors='replace').strip())
    return result.stdout if data else result.stdout.decode()


def commit_of(tag):
    try:
        return git(REFERENCE, 'rev-parse', '--verify', '-q', tag + '^{commit}').strip()
    except PropagationError:
        raise PropagationError(f'tag {tag} does not exist in {REFERENCE}') from None


def tree(tag):
    """{path: (mode, blob)} for every file at the tag."""
    files = {}
    for line in git(REFERENCE, 'ls-tree', '-r', tag).splitlines():
        meta, path = line.split('\t', 1)
        mode, kind, blob = meta.split()
        if kind == 'blob':
            files[path] = (mode, blob)
    return files


def shared_set(tag, files):
    """Shared paths at the tag, as listed by its tests/test_alignment.py."""
    source = git(REFERENCE, 'show', f'{tag}:{ALIGNMENT_FILE}')
    values = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id in ('SHARED_DIRECTORIES', 'SHARED_TESTS'):
            values[node.targets[0].id] = ast.literal_eval(node.value)
    if set(values) != {'SHARED_DIRECTORIES', 'SHARED_TESTS'}:
        raise PropagationError(f'{tag}:{ALIGNMENT_FILE} does not declare SHARED_DIRECTORIES and SHARED_TESTS')
    directories = tuple(values['SHARED_DIRECTORIES'])
    shared = {path for path in files if path.split('/', 1)[0] in directories
              and not any(part in SKIPPED_PARTS for part in path.split('/'))}
    tests = {path for path in values['SHARED_TESTS'] if path in files}
    return directories, shared | tests, tests


def read_manifest(target):
    path = target / MANIFEST_FILE
    if not path.is_file():
        raise PropagationError(f'{MANIFEST_FILE} is missing in {target}')
    text = path.read_text()
    tags, commits = TAG_LINE.findall(text), COMMIT_LINE.findall(text)
    if len(tags) != 1 or len(commits) != 1:
        raise PropagationError(f'{MANIFEST_FILE}: expected one REFERENCE_TAG and one REFERENCE_COMMIT line')
    siblings = SIBLING_LINE.findall(text)
    if len(siblings) != 1:
        raise PropagationError(f"{MANIFEST_FILE}: expected one SIBLING = ROOT.parent / '<reference>' line")
    lines = text.splitlines(keepends=True)
    try:
        start = next(i for i, line in enumerate(lines) if line.rstrip('\n') == 'MANIFEST = {')
        end = next(i for i in range(start + 1, len(lines)) if lines[i].rstrip('\n') == '}')
    except StopIteration:
        raise PropagationError(f'{MANIFEST_FILE}: cannot find the MANIFEST = {{ ... }} block') from None
    entries = {}
    for line in lines[start + 1:end]:
        match = ENTRY.match(line.rstrip('\n'))
        if not match:
            raise PropagationError(f'{MANIFEST_FILE}: unreadable manifest line: {line.strip()}')
        if match[1] in entries:
            raise PropagationError(f'{MANIFEST_FILE}: duplicate manifest entry {match[1]}')
        entries[match[1]] = match[2]
    return text, lines, (start, end), tags[0], commits[0], entries, siblings[0]


def plan(target, old, new):
    target = Path(target).resolve()
    if not (target / '.git').exists():
        raise PropagationError(f'{target} is not a git checkout')
    old_commit, new_commit = commit_of(old), commit_of(new)
    if git(target, 'status', '--porcelain').strip():
        raise PropagationError(f'{target} has uncommitted changes; commit or stash them first')
    _, _, _, tag, commit, adopted, sibling = read_manifest(target)
    if (tag, commit) != (old, old_commit):
        raise PropagationError(f'{target} adopts {tag} ({commit}), not {old} ({old_commit})')
    branch = 'adopt-' + new
    if git(target, 'branch', '--list', branch).strip():
        raise PropagationError(f'branch {branch} already exists in {target}')
    old_files, new_files = tree(old), tree(new)
    directories, old_shared, old_tests = shared_set(old, old_files)
    new_directories, new_shared, _ = shared_set(new, new_files)
    for path in sorted(adopted):
        if path not in old_files:
            raise PropagationError(f'manifest entry {path} is not in {old}')
        expected = git(REFERENCE, 'show', f'{old}:{path}', data=True)
        local = target / path
        if not local.is_file() or local.read_bytes() != expected:
            raise PropagationError(f'{path} differs from {old} in {target}; a fork must be fixed in sandbox-container first')
    complete_directories = {d for d in directories
                            if {p for p in old_shared if p.startswith(d + '/')} <= set(adopted)}
    # A shared directory that the new tag introduces is adopted with the tag.
    complete_directories |= set(new_directories) - set(directories)
    complete_tests = old_tests <= set(adopted)
    modified = sorted(p for p in adopted if p in new_files and new_files[p][1] != old_files[p][1])
    removed = sorted(p for p in adopted if p not in new_files)
    added, not_adopted = [], []
    for path in sorted(new_shared - old_shared):
        top = path.split('/', 1)[0]
        if top in complete_directories or (path.startswith('tests/') and top not in directories and complete_tests):
            added.append(path)
        else:
            not_adopted.append(path)
    changed = {p for p in (old_shared | new_shared) if old_files.get(p) != new_files.get(p)}
    not_adopted += sorted(changed - set(adopted) - set(added) - set(not_adopted))
    documents = {}
    for name in DOCUMENTS:
        path = target / name
        if path.is_file():
            # Also for the same tag, so that a contract the tool cannot read is refused.
            _, replaced, kept = rewrite(target, name, path.read_text(), old, new, old_commit, new_commit)
            if old != new and (replaced or kept):
                documents[name] = (replaced, kept)
    return dict(target=target, old=old, new=new, old_commit=old_commit, new_commit=new_commit, branch=branch,
                modified=modified, added=added, removed=removed, not_adopted=sorted(not_adopted),
                documents=documents, entries=checklist(target, modified + added + removed, qualified_code(new)),
                review=review_lines(target, added + removed, set(adopted) | set(added), old_shared | new_shared),
                changes=range_changes(target, old, new),
                new_files=new_files, sibling=sibling, reference_name=REFERENCE.name)


def review_lines(target, changed, shared, shared_paths):
    """'<path>:<line>' of the target's own lines that name a shared file of a directory with additions or removals.

    Such a line may belong to a hand-written list of that directory, which the
    added or removed file makes stale (docs/propagation.md, step 2).
    """
    directories = {str(Path(path).parent) for path in changed}
    needles = sorted(path for path in shared_paths if str(Path(path).parent) in directories)
    if not needles:
        return []
    found = []
    for name in git(target, 'ls-files', '-z').split('\0'):
        if not name or name in shared or name == MANIFEST_FILE or name in REVIEW_EXCLUDED \
                or name.startswith('openspec/'):
            continue
        try:
            text = (target / name).read_text()
        except (OSError, UnicodeDecodeError):
            continue
        found += [f'{name}:{number}' for number, line in enumerate(text.splitlines(), 1)
                  if any(needle in line for needle in needles)]
    return found


def range_changes(target, old, new):
    """The reference's OpenSpec changes touched between the tags: (name, location, [(capability, in target)]).

    The location is read at this checkout's HEAD, because a change can be
    archived after its tag.
    """
    names = []
    for path in git(REFERENCE, 'log', '--name-only', '--format=', f'{old}..{new}', '--', CHANGES).splitlines():
        parts = path.split('/')
        if len(parts) >= 5 and parts[2] == 'archive':
            name = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', parts[3])
        elif len(parts) >= 4 and parts[2] != 'archive':
            name = parts[2]
        else:
            continue
        if name not in names:
            names.append(name)
    found = []
    for name in sorted(names):
        root = REFERENCE / CHANGES / name
        if root.is_dir():
            location = 'active'
        else:
            archived = sorted(path for path in (REFERENCE / CHANGES / 'archive').glob('*-' + name)
                              if re.fullmatch(r'\d{4}-\d{2}-\d{2}-' + re.escape(name), path.name))
            root = archived[-1] if archived else None
            location = 'archive/' + root.name if root else 'not found at HEAD'
        capabilities = []
        if root is not None and (root / 'specs').is_dir():
            for spec in sorted((root / 'specs').rglob('spec.md')):
                capability = spec.parent.relative_to(root / 'specs').as_posix()
                capabilities.append((capability, (target / 'openspec/specs' / capability / 'spec.md').is_file()))
        found.append((name, location, capabilities))
    return found


def adopted_checklist(target, old, new):
    """The checklist of a target that has already adopted the new tag, for tools/adoption-run.sh."""
    target = Path(target).resolve()
    if not (target / '.git').exists():
        raise PropagationError(f'{target} is not a git checkout')
    old_commit, new_commit = commit_of(old), commit_of(new)
    _, _, _, tag, commit, adopted, _ = read_manifest(target)
    if (tag, commit) != (new, new_commit):
        raise PropagationError(f'{target} adopts {tag} ({commit}), not {new} ({new_commit})')
    old_files, new_files = tree(old), tree(new)
    _, old_shared, _ = shared_set(old, old_files)
    _, new_shared, _ = shared_set(new, new_files)
    changed = sorted({path for path in adopted if old_files.get(path) != new_files.get(path)}
                     | (old_shared - new_shared))
    return checklist(target, changed, qualified_code(new))


def tag_pattern(tag):
    # Whole word: sandbox-ref-1 must not match sandbox-ref-10.
    return re.compile(r'(?<![\w-])' + re.escape(tag) + r'(?![\w-])')


def rewrite(target, name, text, old, new, old_commit, new_commit):
    """(new text, references replaced, old-tag mentions kept or None) for a current-state document."""
    if name == CONTRACT:
        return rewrite_contract(target, text, old, new, old_commit, new_commit)
    tag = tag_pattern(old)
    replaced = len(tag.findall(text)) + text.count(old_commit)
    return tag.sub(new, text).replace(old_commit, new_commit), replaced, None


def row_cells(line):
    """The cells of a Markdown table row such as '| a | b |', or None for any other line."""
    body = line.rstrip('\r\n')
    if not (body.startswith('| ') and body.endswith(' |')):
        return None
    return body[2:-2].split(' | ')


def display_name(target):
    """The target's parity row label: its profile's display_name, read as data."""
    try:
        value = json.loads((target / PROFILE_FILE).read_text())
    except (OSError, ValueError) as error:
        raise PropagationError(f'cannot read {PROFILE_FILE} in {target} to find its parity row in {CONTRACT}: '
                               f'{error}') from None
    name = value.get('display_name') if isinstance(value, dict) else None
    if not isinstance(name, str) or not name.strip():
        raise PropagationError(f'{PROFILE_FILE} in {target} has no display_name to find its parity row in {CONTRACT}')
    return name


def parity_table(target, lines):
    """None without a parity table; else its adoption column, the indexes of the
    target's and the reference's rows, and the table's line range."""
    headers = [i for i, line in enumerate(lines) if (row_cells(line) or [])[:2] == PARITY_HEADER]
    if not headers:
        return None
    if len(headers) > 1:
        raise PropagationError(f'{CONTRACT} has {len(headers)} parity tables; expected one')
    start = headers[0]
    header = row_cells(lines[start])
    end, labels = start + 2, []
    while end < len(lines) and lines[end].startswith('|'):
        cells = row_cells(lines[end])
        if cells is None or len(cells) != len(header):
            raise PropagationError(f'{CONTRACT} line {end + 1}: a parity row needs the {len(header)} cells of the '
                                   'header, separated by " | "')
        labels.append((end, cells[0]))
        end += 1
    name = display_name(target)
    own = [i for i, label in labels if label == name]
    if len(own) != 1:
        raise PropagationError(f'{CONTRACT} has {len(own)} parity rows for {name!r}, the display_name of '
                               f'{PROFILE_FILE}; expected one')
    reference = [i for i, label in labels if label.endswith(REFERENCE_ROW)]
    if len(reference) > 1:
        raise PropagationError(f'{CONTRACT} has {len(reference)} reference parity rows; expected at most one')
    return PARITY_HEADER.index('Contract adoption'), own + reference, range(start, end)


def rewrite_contract(target, text, old, new, old_commit, new_commit):
    """Replace only the current references of the network contract.

    In the parity table, the old tag moves only in the contract adoption cell of
    the target's row and of the reference row: the other cells, such as real
    enforcement, record the tag each result ran at. Elsewhere it moves only where
    the reference line names it with its commit. The old commit moves anywhere."""
    lines = text.splitlines(keepends=True)
    table = parity_table(target, lines)
    tag = tag_pattern(old)
    pair = re.compile('`' + re.escape(old) + r'`(?= \(commit `' + re.escape(old_commit) + r'`\))')
    replaced = 0
    for index, line in enumerate(lines):
        if table and index in table[1]:
            cells = row_cells(line)
            cells[table[0]], count = tag.subn(new, cells[table[0]])
            lines[index] = '| ' + ' | '.join(cells) + ' |' + line[len(line.rstrip('\r\n')):]
        elif table and index in table[2]:
            continue
        else:
            lines[index], count = pair.subn(f'`{new}`', line)
        replaced += count
    kept = len(tag.findall(text)) - replaced
    result = ''.join(lines)
    replaced += result.count(old_commit)
    return result.replace(old_commit, new_commit), replaced, kept


def runner_modes(target):
    path = target / 'tests/run-runtime.sh'
    if not path.is_file():
        return set()
    text = path.read_text()
    labels = re.findall(r'^\s*(--[a-z][a-z-]*)(?:\|[^)]*)?\)', text, re.M)
    labels += re.findall(r'\|(--[a-z][a-z-]*)\)', text)
    # [[ "$1" == --mode ]], also when || joins a second test of the same argument.
    labels += re.findall(r'==\s*(--[a-z][a-z-]*)\s*(?:\]\]|\|\|)', text)
    return set(labels)


def qualified_code(tag):
    """The copied files the qualification gate digests at the tag (SHARED_CODE), or () without them.

    Only the literal paths: the computed entries name the built guard binary
    and the wrapper's own profile and policy, which are not copied files.
    """
    try:
        source = git(REFERENCE, 'show', f'{tag}:{QUALIFICATION_FILE}')
    except PropagationError:
        return ()
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id == 'SHARED_CODE' and isinstance(node.value, (ast.Tuple, ast.List)):
            return tuple(element.value for element in node.value.elts
                         if isinstance(element, ast.Constant) and isinstance(element.value, str))
    return ()


def profile_images(target):
    """The images of the target's profile, read as data; {} when it names none."""
    try:
        images = json.loads((target / PROFILE_FILE).read_text()).get('images')
    except (OSError, ValueError, AttributeError):
        return {}
    return images if isinstance(images, dict) else {}


def naming_modules(target, helper):
    """The target's test modules that name a test helper: by import, or by reading its file."""
    word = re.compile(r'\b' + re.escape(Path(helper).stem) + r'\b')
    return sorted('tests/' + path.name for path in (target / 'tests').glob('test_*.py')
                  if word.search(path.read_text(errors='replace')))


def mode_entry(mode, selection=''):
    name = mode.removeprefix('--') or 'runtime'
    return Entry('mode', name, ' '.join(['bash', RUNNER] + [part for part in (mode, selection) if part]))


def checklist(target, changed, shared_code=()):
    """The entries that validate an adoption: what exercises each changed file (docs/propagation.md)."""
    offered = runner_modes(target)
    has_runner = (target / RUNNER).is_file()

    def available(mode):
        return has_runner and (mode == '' or mode in offered)

    def any_changed(*prefixes):
        return any(path.startswith(prefixes) for path in changed)
    modes, selections, unit, prepare, manual = set(), {}, ['tests.test_reference_copy', 'tests.test_alignment'], [], []
    if any_changed('setup/', 'tests/test_setup.py'):
        modes |= {'--setup', '--setup-runtime'}
    if any_changed('network/qualif', 'network/platform_check.py', 'network/release_acceptance.json',
                   'tests/test_qualification.py', 'tests/test_platform.py') \
            or any(path in shared_code for path in changed):
        modes.add('--qualification')
    if any_changed('network/guard', 'network/build-guard.sh', 'network/proxy', 'network/relay.py', 'network/mux.py',
                   'network/session.py', 'network/control.py', 'network/tls_client_hello.py', 'network/policy.py',
                   'tests/test_guard.py', 'tests/guard_', 'tests/test_session.py', 'tests/test_mux.py'):
        modes |= {'--guard', '--network'}
    if any_changed('network/agent_profile.py'):
        modes.add('--wrapper')
    # The launcher core runs in every session: its shared tests and the default runtime mode.
    if any(path.startswith('launcher/') and not path.startswith(('launcher/engine/', 'launcher/windows/'))
           for path in changed):
        modes |= {'--wrapper', ''}
    if any_changed(*ENGINE_INPUTS):
        agent = profile_images(target).get('agent')
        if not agent:
            raise PropagationError(f'{PROFILE_FILE} names no images.agent, so the engine image cannot be named')
        prepare.append(Entry('prepare', 'engine', f'podman build --pull=never --tag {agent}-engine:latest launcher/engine'))
        for mode, name, path, pattern, selection in ENGINE_CASES:
            source = target / path
            if source.is_file() and re.search(pattern, source.read_text(errors='replace')):
                selections[mode] = (name, selection)
            else:
                modes.add(mode)
    if any_changed('launcher/windows/') or any(path.endswith('.ps1') for path in changed):
        manual.append(Entry('manual', 'windows', WINDOWS_STEP))
    for path in sorted(changed):
        if not (path.startswith('tests/') and path.endswith('.py') and path.count('/') == 1):
            continue
        name = Path(path).name
        for module in [path] if name.startswith('test_') else naming_modules(target, name):
            mode = MODE_TESTS.get(module)
            if mode is not None and available(mode):
                modes.add(mode)
            else:
                unit.append('tests.' + Path(module).stem)
    entries = []
    if '--shared' in offered:
        # The target's unit discovery in its runner image, which also runs the changed modules.
        entries.append(mode_entry('--shared'))
    else:
        entries.append(Entry('unit', 'unit', 'python3 -m unittest ' + ' '.join(dict.fromkeys(unit))))
    for mode in MODE_ORDER:
        if not available(mode):
            continue
        if mode in modes:
            entries.append(mode_entry(mode))
        elif mode in selections:
            name, selection = selections[mode]
            entries.append(mode_entry(mode, selection)._replace(name=name))
    images = profile_images(target)
    needed = []
    if images.get('agent'):
        needed.append(Entry('image', 'runtime', images['agent'] + ':latest'))
    if images.get('toolchain') and any(entry.name in ('qualification', 'guard', 'network', 'network-engine')
                                       for entry in entries):
        needed.append(Entry('image', 'toolchain', images['toolchain'] + ':development'))
    return needed + prepare + entries + manual


def display(entry):
    """How the report prints an entry's command."""
    return PRIVATE_STORAGE + entry.command if entry.kind == 'unit' else entry.command


def write_atomic(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name + '.')
    try:
        with os.fdopen(handle, 'wb') as output:
            output.write(data)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def apply(result):
    target, new = result['target'], result['new']
    git(target, 'switch', '-q', '-c', result['branch'])
    written = []
    try:
        for path in result['modified'] + result['added']:
            mode = 0o755 if result['new_files'][path][0] == '100755' else 0o644
            write_atomic(target / path, git(REFERENCE, 'show', f'{new}:{path}', data=True), mode)
            written.append(path)
        for path in result['removed']:
            (target / path).unlink()
            written.append(path)
        text, lines, (start, end), _, _, entries, sibling = read_manifest(target)
        for path in result['removed']:
            entries.pop(path)
        for path in result['modified'] + result['added']:
            entries[path] = hashlib.sha256((target / path).read_bytes()).hexdigest()
        block = [f"    '{path}': '{digest}',\n" for path, digest in sorted(entries.items())]
        text = ''.join(lines[:start + 1] + block + lines[end:])
        text = TAG_LINE.sub(f"REFERENCE_TAG = '{new}'", text)
        text = COMMIT_LINE.sub(f"REFERENCE_COMMIT = '{result['new_commit']}'", text)
        if sibling != result['reference_name']:
            # The manifest names the repository this tool runs from: its sibling
            # path, docstring and skip message.
            text = text.replace(sibling, result['reference_name'])
            text = COPY_LINE.sub(f"the {result['reference_name']} reference copy", text, count=1)
        manifest = target / MANIFEST_FILE
        write_atomic(manifest, text.encode(), manifest.stat().st_mode & 0o7777)
        written.append(MANIFEST_FILE)
        for name, (replaced, _) in result['documents'].items():
            if not replaced:
                continue
            path = target / name
            text, _, _ = rewrite(target, name, path.read_text(), result['old'], new,
                                 result['old_commit'], result['new_commit'])
            write_atomic(path, text.encode(), path.stat().st_mode & 0o7777)
            written.append(name)
    except BaseException as error:
        raise PropagationError(f'apply stopped after writing {written}: {error}; '
                               f'reset with git -C {target} checkout -- . and switch back') from error


def report(result, applied):
    out = [f"{'Applied' if applied else 'Dry run'}: {result['old']} -> {result['new']} in {result['target']}"]
    if applied:
        out.append(f"Branch: {result['branch']} (uncommitted; review with git diff)")
    for label in ('modified', 'added', 'removed', 'not_adopted'):
        out.append(f"{label.replace('_', ' ')}: " + (', '.join(result[label]) or 'none'))
    out.append('documents: ' + (', '.join(f'{n} ({r})' if k is None else f'{n} ({r}, {k} kept)'
                                          for n, (r, k) in result['documents'].items()) or 'none'))
    out.append('manifest: ' + MANIFEST_FILE + f" -> {result['new']} ({result['new_commit']})")
    out += ['review: ' + line for line in result['review']]
    out.append('reference changes: ' + ('none' if not result['changes'] else str(len(result['changes']))))
    for name, location, capabilities in result['changes']:
        specs = ', '.join(capability + ('' if present else ' [not in target]') for capability, present in capabilities)
        out.append(f'  {name}: {location}; specs: {specs or "none"}')
    if result['sibling'] != result['reference_name']:
        out.append(f"manifest: names {result['reference_name']} instead of {result['sibling']}")
    entries = result['entries']
    runs = [entry for entry in entries if entry.kind in ('unit', 'mode')]
    prepared = [entry.command for entry in entries if entry.kind == 'prepare']
    if prepared:
        out.append('Prepare in the target: ' + '; '.join(prepared))
    out.append('Run in the target: ' + '; '.join(display(entry) for entry in runs))
    images = [entry.command for entry in entries if entry.kind == 'image']
    if images:
        out.append('Images needed: ' + ', '.join(images))
    out += ['Manual: ' + entry.command for entry in entries if entry.kind == 'manual']
    out.append(f"On one host, after the adoption: bash tools/adoption-run.sh {result['target']} "
               f"{result['old']} {result['new']}")
    copied = result['modified'] + result['added']
    out += ['', 'Validation record template (docs/validation.md):', '',
            f"## Adoption of `{result['new']}`: {datetime.date.today().isoformat()}", '',
            f"Copied from `sandbox-container` tag `{result['new']}` (commit `{result['new_commit'][:7]}`): "
            + (', '.join(f'`{p}`' for p in copied) or 'no files') + '.'
            + (' Removed: ' + ', '.join(f'`{p}`' for p in result['removed']) + '.' if result['removed'] else ''),
            'The `tests/test_reference_copy.py` manifest moved to the tag.', '',
            '| Check | Result |', '| --- | --- |']
    out += [f'| `{display(entry)}` | <fill in> |' for entry in runs]
    out += [f'| {entry.command} | <fill in> |' for entry in entries if entry.kind == 'manual']
    out += ['', 'Commit message:', '', f"Adopt {result['new']}", '',
            f"Copy the changed shared files from sandbox-container {result['new']} and move",
            'the reference manifest and the current-state references to the tag.']
    print('\n'.join(out))


def main(argv=None):
    global REFERENCE
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('target')
    parser.add_argument('old')
    parser.add_argument('new')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--apply', action='store_true', help='write the changes on a new adopt-<new> branch')
    action.add_argument('--checklist', action='store_true',
                        help='print the validation commands of a target that has adopted <new>, one per line')
    parser.add_argument('--reference', default=str(REFERENCE), help=argparse.SUPPRESS)  # tests only
    args = parser.parse_args(argv)
    REFERENCE = Path(args.reference).resolve()
    try:
        if args.checklist:
            for entry in adopted_checklist(args.target, args.old, args.new):
                print('\t'.join(entry))
            return 0
        result = plan(args.target, args.old, args.new)
        if args.apply:
            apply(result)
        report(result, args.apply)
    except PropagationError as error:
        print('propagate: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
