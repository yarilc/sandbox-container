"""Credential-free checks for tools/adoption-run.sh, with stub podman, runner and Python.

Reference-only, like tests/test_propagate.py, whose disposable repositories it
reuses. The stubs need executable storage: SANDBOX_TEST_TMPDIR overrides the
temporary directory when /tmp is mounted noexec.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_propagate as base  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RUNNER_TOOL = ROOT / 'tools/adoption-run.sh'
ALIGNMENT = """SHARED_DIRECTORIES = ('network', 'setup', 'launcher')
SHARED_TESTS = ('tests/test_alignment.py', 'tests/test_shared.py')
"""
PROFILE = ('{"name": "pi-container", "display_name": "Pi", '
           '"images": {"agent": "localhost/pi", "toolchain": "localhost/pi-guard-toolchain"}}\n')
# Every call is appended to $STUB_LOG. STUB_MISSING lists absent images.
PODMAN = r"""#!/usr/bin/env bash
printf 'podman %s\n' "$*" >> "$STUB_LOG"
case "$1 ${2:-}" in
    'image exists') [[ ",${STUB_MISSING:-}," != *",$3,"* ]] ;;
    'image inspect') echo 'sha256:feed label=SETUID,SETGID,SYS_CHROOT,CHOWN' ;;
    'images '*) echo 'localhost/pi:latest' ;;
    'build '*) echo 'sha256:feed' ;;
    'run '*) printf 'test_a (tests.test_shared.T.test_a) ... ok\n\nOK\n' ;;
    *) echo "podman stub: $*" ;;
esac
"""
# The wrapper's runner: it offers its modes as Claude's does. STUB_FAIL names a
# mode that fails, STUB_UNPREPARED one whose test skips for a missing image.
RUNNER = r"""#!/usr/bin/env bash
printf 'runner %s\n' "$*" >> "$STUB_LOG"
if [[ "${1:-}" == --setup ]]; then :
elif [[ "${1:-}" == --setup-runtime ]]; then :
elif [[ "${1:-}" == --network ]]; then :
fi
mode=${1:-runtime}
[[ "$mode" == -* && "$mode" != -k ]] || mode=runtime
echo "test_x (tests.m.C.test_x) ... ok"
echo "test_y (tests.m.C.test_y) ... skipped 'opt-in check'"
if [[ "$mode" == "${STUB_UNPREPARED:-none}" ]]; then
    echo "test_z (tests.m.C.test_z) ... skipped 'prepare docker.io/library/alpine in the engine first'"
fi
if [[ "$mode" == "${STUB_FAIL:-none}" ]]; then
    printf '\nFAILED (failures=1)\n'
    exit 1
fi
printf '\nOK (skipped=1)\n'
"""
# The host Python: -c answers the version check (STUB_OLD=1 for Python 3.9).
PYTHON = r"""#!/usr/bin/env bash
if [[ "$1" == -c ]]; then exit "${STUB_OLD:-0}"; fi
if [[ "$1" == --version ]]; then
    [[ "${STUB_OLD:-0}" == 1 ]] && echo 'Python 3.9.18' || echo 'Python 3.12.3'
    exit 0
fi
printf 'python %s tmpdir=%s\n' "$*" "$SANDBOX_TEST_TMPDIR" >> "$STUB_LOG"
[[ -d "$SANDBOX_TEST_TMPDIR" ]] && echo 'private storage present' >> "$STUB_LOG"
printf 'test_a (tests.test_shared.T.test_a) ... ok\n\nOK\n'
"""


class AdoptionRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='adoption-run-', dir=os.environ.get('SANDBOX_TEST_TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        base_dir = Path(self.tmp.name)
        self.reference, self.target = base_dir / 'reference', base_dir / 'target'
        self.home, self.stubs, self.log = base_dir / 'home', base_dir / 'stubs', base_dir / 'stub.log'
        for path in (self.home, self.stubs):
            path.mkdir()
        for repo in (self.reference, self.target):
            repo.mkdir()
            base.git(repo, 'init', '-q', '-b', 'main')
            base.git(repo, 'config', 'user.email', 'test@example.invalid')
            base.git(repo, 'config', 'user.name', 'Test')
        old = {'network/a.py': 'a = 1\n', 'setup/common.py': 'common = 1\n', 'launcher/core.sh': 'core\n',
               'launcher/engine/Containerfile': 'FROM scratch\n', 'tests/test_alignment.py': ALIGNMENT,
               'tests/test_shared.py': 'shared = 1\n'}
        self.commit_tag(old, 'sandbox-ref-1')
        # setup/ changed, an engine input added, a shared test module changed.
        new = dict(old, **{'setup/common.py': 'common = 2\n', 'launcher/engine/start.sh': 'start\n',
                           'tests/test_shared.py': 'shared = 2\n'})
        self.commit_tag(new, 'sandbox-ref-2')
        self.files = {'sandbox-ref-1': old, 'sandbox-ref-2': new}
        self.adopt('sandbox-ref-2')
        for name, text in (('podman', PODMAN), ('python', PYTHON)):
            (self.stubs / name).write_text(text)
            (self.stubs / name).chmod(0o755)

    def commit_tag(self, files, tag):
        for path in list(self.reference.rglob('*')):
            if path.is_file() and '.git' not in path.parts:
                path.unlink()
        base.write(self.reference, files)
        base.git(self.reference, 'add', '-A')
        base.git(self.reference, 'commit', '-q', '-m', tag)
        base.git(self.reference, 'tag', '-a', tag, '-m', tag)

    def adopt(self, tag):
        """Commit the target as an adopter of the tag, with its own runner and engine tests."""
        files = self.files[tag]
        commit = base.git(self.reference, 'rev-parse', tag + '^{commit}').strip()
        base.write(self.target, dict(files, **{
            'tests/test_reference_copy.py': base.Propagation.manifest(tag, commit, files),
            'tests/run-runtime.sh': RUNNER, 'agent/profile.json': PROFILE,
            'tests/test_runtime.py': 'class SessionEngineTests:\n    pass\n',
            'tests/test_network_runtime.py': ('class NetworkRuntime:\n'
                                              '    def test_offline_session_engine_has_no_external_path(self):\n'
                                              '        pass\n')}))
        (self.target / 'tests/run-runtime.sh').chmod(0o755)
        base.git(self.target, 'add', '-A')
        base.git(self.target, 'commit', '-q', '-m', 'adopt ' + tag)

    def run_tool(self, *args, old='sandbox-ref-1', new='sandbox-ref-2', **env):
        status = base.git(self.target, 'status', '--porcelain')
        values = dict(os.environ, HOME=str(self.home), PATH=f'{self.stubs}:{os.environ["PATH"]}',
                      STUB_LOG=str(self.log), SANDBOX_ADOPTION_REFERENCE=str(self.reference),
                      SANDBOX_ADOPTION_HOST_PYTHON=str(self.stubs / 'python'), SANDBOX_ADOPTION_MIN_FREE_KIB='0')
        values.update(env)
        result = subprocess.run(['bash', str(RUNNER_TOOL), *args, str(self.target), old, new],
                                capture_output=True, text=True, env=values, timeout=120)
        # The runner never changes the checkout.
        self.assertEqual(base.git(self.target, 'status', '--porcelain'), status)
        return result

    def runs(self):
        return sorted(path for path in self.home.glob('sbx-logs-*') if path.is_dir())

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_every_entry_passes(self):
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        (logs,) = self.runs()
        host = subprocess.run(['hostname', '-s'], capture_output=True, text=True).stdout.strip()
        self.assertTrue(logs.name.startswith(f'sbx-logs-target-sandbox-ref-2-{host}-'), logs.name)
        self.assertTrue(Path(str(logs) + '.tar.gz').is_file())
        for name in ('unit', 'setup', 'setup-runtime', 'runtime-engine', 'network-engine', 'prepare-engine'):
            self.assertTrue((logs / (name + '.log')).is_file(), name)
        summary = (logs / 'summary.txt').read_text()
        self.assertIn('prepare engine exit=0\n', summary)
        self.assertIn('engine image: sha256:feed label=SETUID,SETGID,SYS_CHROOT,CHOWN\n', summary)
        self.assertIn('unit exit=0 OK (host Python 3.12.3)\n', summary)
        self.assertIn('setup exit=0 OK (skipped=1)\n', summary)
        self.assertIn('setup-runtime tags: equal before and after\n', summary)
        self.assertIn('  skipped: test_y (tests.m.C.test_y): opt-in check\n', summary)
        self.assertIn('result: passed\n', summary)
        calls = self.calls()
        build = next(i for i, call in enumerate(calls) if call.startswith('podman build '))
        self.assertLess(build, next(i for i, call in enumerate(calls) if call.startswith('runner ')))
        self.assertIn('podman build --pull=never --tag localhost/pi-engine:latest launcher/engine', calls)
        self.assertIn('runner -k SessionEngineTests', calls)
        self.assertIn('runner --network -k test_offline_session_engine_has_no_external_path', calls)
        unit = next(call for call in calls if call.startswith('python '))
        self.assertIn('-m unittest tests.test_reference_copy tests.test_alignment tests.test_shared -v', unit)
        private = unit.split('tmpdir=')[1]
        self.assertTrue(private.startswith(str(self.home / '.sbx-test-')), private)
        self.assertIn('private storage present', calls)
        self.assertFalse(Path(private).exists())
        self.assertFalse([call for call in calls if call.startswith(('podman rmi', 'podman rm '))])

    def test_failure_in_the_middle_runs_the_rest(self):
        result = self.run_tool(STUB_FAIL='--setup')
        self.assertEqual(result.returncode, 1)
        (logs,) = self.runs()
        summary = (logs / 'summary.txt').read_text()
        self.assertIn('setup exit=1 FAILED (failures=1)\n', summary)
        self.assertIn('network-engine exit=0', summary)
        self.assertIn('result: failed\n', summary)

    def test_skip_for_an_image_not_prepared_fails_the_run(self):
        result = self.run_tool(STUB_UNPREPARED='--network')
        self.assertEqual(result.returncode, 1)
        summary = (self.runs()[0] / 'summary.txt').read_text()
        self.assertIn('  NOT PREPARED: test_z (tests.m.C.test_z): prepare docker.io/library/alpine in the engine first\n',
                      summary)
        self.assertIn('result: failed\n', summary)

    def test_preflight_failures_run_nothing(self):
        for env, message in (({'STUB_MISSING': 'localhost/pi-guard-toolchain:development'},
                               'preflight: missing toolchain image localhost/pi-guard-toolchain:development'),
                              ({'SANDBOX_ADOPTION_MIN_FREE_KIB': str(10 ** 15)}, 'KiB free in')):
            with self.subTest(message=message):
                self.log.unlink(missing_ok=True)
                before = self.runs()
                result = self.run_tool(**env)
                self.assertEqual(result.returncode, 1)
                (logs,) = [path for path in self.runs() if path not in before]
                summary = (logs / 'summary.txt').read_text()
                self.assertIn(message, summary)
                self.assertIn('preflight failed: no command run\n', summary)
                self.assertTrue(Path(str(logs) + '.tar.gz').is_file())
                self.assertFalse([call for call in self.calls() if call.startswith(('runner ', 'python ', 'podman build'))])

    def test_only_reruns_chosen_entries_in_a_new_directory(self):
        self.assertEqual(self.run_tool().returncode, 0)
        self.log.unlink()
        result = self.run_tool('--only', 'unit')
        self.assertEqual(result.returncode, 0, result.stderr)
        first, second = self.runs()
        self.assertEqual(sorted(path.name for path in second.glob('*.log')), ['prepare-engine.log', 'unit.log'])
        self.assertTrue((first / 'setup.log').is_file())
        self.assertFalse([call for call in self.calls() if call.startswith('runner ')])
        result = self.run_tool('--only', 'unit,bogus')
        self.assertEqual(result.returncode, 2)
        self.assertIn('no checklist entry bogus', result.stderr)
        self.assertIn('unit setup setup-runtime runtime-engine network-engine', result.stderr)
        self.assertEqual(len(self.runs()), 2)

    def test_old_host_python_runs_the_unit_tests_in_the_runtime_image(self):
        result = self.run_tool('--only', 'unit', STUB_OLD='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = (self.runs()[0] / 'summary.txt').read_text()
        self.assertIn('unit exit=0 OK (runtime image localhost/pi:latest (host Python 3.9.18 is older than 3.11))\n',
                      summary)
        run = next(call for call in self.calls() if call.startswith('podman run '))
        self.assertIn('--network=none', run)
        self.assertIn('--env SANDBOX_TEST_TMPDIR=/sandbox-test-tmp --entrypoint python3 localhost/pi:latest '
                      '-m unittest tests.test_reference_copy tests.test_alignment tests.test_shared -v', run)
        self.assertIn(f'--volume {self.reference}:{self.reference}:ro', run)
        self.assertFalse([call for call in self.calls() if call.startswith('python ')])

    def test_no_engine_build_without_engine_inputs(self):
        self.files['sandbox-ref-3'] = dict(self.files['sandbox-ref-2'], **{'setup/common.py': 'common = 3\n'})
        self.commit_tag(self.files['sandbox-ref-3'], 'sandbox-ref-3')
        self.adopt('sandbox-ref-3')
        result = self.run_tool(old='sandbox-ref-2', new='sandbox-ref-3')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = (self.runs()[0] / 'summary.txt').read_text()
        self.assertNotIn('prepare engine', summary)
        self.assertFalse([call for call in self.calls() if call.startswith('podman build ')])
        self.assertIn('runner --setup', self.calls())

    def test_checkout_on_the_old_tag_is_refused(self):
        self.adopt('sandbox-ref-1')
        result = self.run_tool()
        self.assertEqual(result.returncode, 1)
        self.assertIn('adopts sandbox-ref-1', result.stderr)
        self.assertIn('not sandbox-ref-2', result.stderr)
        self.assertEqual(self.runs(), [])
        self.assertEqual(self.calls(), [])


if __name__ == '__main__':
    unittest.main()
