"""Reference-specific launcher checks: the real entry script with the shell profile.

The launcher behavior is tested once, for every wrapper, by the shared
tests/test_launcher.py against fixture agent parts. These cases cover what only
the reference's own profile shows: help, the offline default, Bash arguments,
shell mode, the Bash history location and symlink invocation.
"""
import json
import itertools
import os
from pathlib import Path
import socket
import stat
import sys
import subprocess
import tempfile
import time
import signal
import shutil
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'sandbox-container.sh'
OWNED_ID = 'a' * 64
FAKE = (ROOT / 'tests/fake_podman.py').read_text()


# Shared accept/reject table for the Bash wrapper and network/agent_budgets.py.
BUDGET_REJECTIONS = {
    'MEMORY_LIMIT': ('', ' ', '0', '0g', '-1', '-1g', 'max', '4', '4t', '4gb', '1.5g', '04g', 'abc', '2000000g'),
    'CPU_LIMIT': ('', '0', '0.0', '0.0000', '-1', 'max', '1.5555', '1.', '.5', '1025', 'two', ' 2'),
    'PIDS_LIMIT': ('', '0', '-1', 'max', '4194305', '01', '1.5', 'x'),
    'RUN_TIMEOUT': ('-1', '1.5', 'x', '01', '2147483648', ' 5'),
}
BUDGET_ACCEPTED = {
    'MEMORY_LIMIT': ('1k', '4g', '4G', '512m', '1048576k', '1048576g'),
    'CPU_LIMIT': ('0.001', '2', '1.5', '1024', '02', '3.25'),
    'PIDS_LIMIT': ('1', '512', '4194304'),
    'RUN_TIMEOUT': ('0', '1', '2147483647'),
}


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='sandbox-wrapper-', dir=os.environ.get('SANDBOX_TEST_TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        podman = self.bin / 'podman'
        podman.write_text(FAKE)
        podman.chmod(0o755)
        self.project = self.base / 'parent with spaces' / 'my project'
        self.project.mkdir(parents=True)
        self.log = self.base / 'calls.jsonl'
        self.state = self.base / 'state'
        self.env = {'PATH': os.environ['PATH'], 'SANDBOX_CONTAINER_NETWORK': 'unrestricted',
                    'SANDBOX_CONTAINER_MAINTENANCE': '1'}
        self.env['HOME'] = str(self.base / 'host-home')
        self.env.pop('SANDBOX_CONTAINER_CONFIG_DIR', None)
        self.env.update(PATH=str(self.bin) + ':' + self.env['PATH'],
                        FAKE_LOG=str(self.log),
                        SANDBOX_CONTAINER_STATE_DIR=str(self.state))
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket_path = self.base / 'podman.sock'
        self.socket.bind(str(self.socket_path))
        self.addCleanup(self.socket.close)
        self.env['SANDBOX_CONTAINER_PODMAN_SOCKET'] = str(self.socket_path)
        self.library = self.base / 'host-home/.local/share/sandbox-toolchains'

    def run_wrapper(self, *args, cwd=None, caller_umask=-1, **env):
        return subprocess.run([str(getattr(self, 'wrapper', WRAPPER)), *args], cwd=cwd or self.project,
                              env=self.env | env, input='input payload',
                              text=True, capture_output=True, timeout=25, umask=caller_umask)

    def calls(self):
        return [json.loads(s) for s in self.log.read_text().splitlines()] if self.log.exists() else []

    def create(self):
        return next(c for c in self.calls() if c[0] == 'create')

    def wait_marker(self, proc, suffix):
        marker = Path(str(self.log) + suffix)
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            if proc.poll() is not None:
                self.fail(str(proc.communicate()))
            time.sleep(0.02)
        self.assertTrue(marker.exists(), suffix)

    def start_waiting_wrapper(self, marker='.started', **env):
        diagnostics = self.base / 'diagnostics'
        diagnostics.mkdir(exist_ok=True)
        proc = subprocess.Popen([str(WRAPPER)], cwd=self.project,
                                env=self.env | {'TMPDIR': str(diagnostics)} | env,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        def finish():
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=25)
            pid_files = [Path(str(self.log) + suffix) for suffix in ('.pid', '.create-pid')]
            pid_files.extend(self.base.glob('calls.jsonl.stalled-*'))
            for pid in pid_files:
                if pid.exists():
                    try:
                        child = int(pid.read_text())
                        if str(self.bin / 'podman').encode() in Path(f'/proc/{child}/cmdline').read_bytes():
                            os.kill(child, signal.SIGKILL)
                    except (ProcessLookupError, FileNotFoundError):
                        pass
        self.addCleanup(finish)
        self.wait_marker(proc, marker)
        return proc, diagnostics

    def assert_no_fake_client(self):
        for suffix in ('.pid', '.create-pid'):
            path = Path(str(self.log) + suffix)
            if path.exists():
                with self.assertRaises(ProcessLookupError):
                    os.kill(int(path.read_text()), 0)

    def test_help_without_podman_or_side_effects(self):
        help_bin = self.base / 'help-bin'
        help_bin.mkdir()
        (help_bin / 'cat').symlink_to('/bin/cat')
        result = subprocess.run(
            ['/bin/bash', str(WRAPPER), '--container-help'],
            env=self.env | {'PATH': str(help_bin), 'CLAUDE_YOLO': 'invalid'},
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('beyond the workspace', result.stdout)
        self.assertFalse(self.calls())
        self.assertFalse(self.state.exists())

    def test_missing_mode_defaults_to_offline_and_needs_an_installation(self):
        for mode in (None, ''):
            with self.subTest(mode=mode):
                env = self.env.copy()
                env.pop('SANDBOX_CONTAINER_NETWORK')
                if mode is not None:
                    env['SANDBOX_CONTAINER_NETWORK'] = mode
                result = subprocess.run(['/bin/bash', str(WRAPPER)], cwd=self.project,
                                        env=env, input='input payload', text=True,
                                        capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('setup required: offline sessions need a protected installation; run bash ',
                              result.stderr)
                self.assertIn('--container-setup', result.stderr)
                self.assertIn('SANDBOX_CONTAINER_NETWORK=unrestricted', result.stderr)
                self.assertEqual(result.stdout, '')
                self.assertFalse(self.calls())
                self.assertFalse(self.state.exists())
                self.assertFalse(Path(env['HOME']).exists())

    def test_argument_forwarding_and_defaults(self):
        result = self.run_wrapper('-p', 'hello world', '', '--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.create()[-5:], ['localhost/sandbox-container:latest', '-p', 'hello world', '', '--help'])
        self.assertNotIn('--tty', self.create())
        self.assertNotIn('--dangerously-skip-permissions', self.create())
        self.assertIn('--unsetenv', self.create())
        self.assertEqual(self.create()[self.create().index('--unsetenv') + 1], 'CONTAINER_HOST')
        self.assertIn('stdin:input payload', result.stdout)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)

    def test_shell_option_is_equivalent(self):
        creates = []
        for flags in ((), ('--container-shell',)):
            self.log.unlink(missing_ok=True)
            result = self.run_wrapper(*flags, '-c', 'echo "$0"', '')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('stdin:input payload', result.stdout)
            create = self.create()
            # The cidfile and the ownership label name the per-session directory.
            creates.append([a for i, a in enumerate(create) if i == 0 or create[i - 1] not in ('--cidfile', '--label')])
        self.assertEqual(creates[0], creates[1])
        self.assertEqual(creates[0][-6:], ['--entrypoint', '/bin/bash', 'localhost/sandbox-container:latest',
                                           '-c', 'echo "$0"', ''])

    def volumes(self):
        create = self.create()
        return [create[i + 1] for i, a in enumerate(create) if a == '--volume']

    def environment(self):
        create = self.create()
        return [create[i + 1] for i, a in enumerate(create) if a == '--env']

    def restricted_fixture(self):
        # Argument/lifecycle instrumentation only. Real guard and protected-path
        # acceptance lives in test_network_runtime; no production check is changed.
        install = self.base / 'synthetic-install'
        (install / 'network/bin').mkdir(parents=True)
        self.wrapper = install / 'sandbox-container.sh'
        shutil.copyfile(WRAPPER, self.wrapper)
        self.wrapper.chmod(0o700)
        guard = install / 'network/bin/sandbox-egress-guard'
        guard.write_text('#!/bin/sh\nexit 0\n')
        guard.chmod(0o700)
        (guard.parent / 'sandbox-egress-guard.sha256').write_text('c' * 64 + '  sandbox-egress-guard\n')
        shutil.copyfile(ROOT / 'network/proxy_hardening.py', install / 'network/proxy_hardening.py')
        shutil.copyfile(ROOT / 'network/platform_check.py', install / 'network/platform_check.py')
        for name in ('network/session.py', 'network/agent_profile.py', 'network/agent_budgets.py', 'network/policy.py',
                     'network/revisions.py', 'agent/profile.json', 'setup/common.py', 'setup/toolchains.py',
                     'Containerfile', 'launcher/core.sh', 'agent/launcher.sh'):
            (install / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, install / name)
        (install / 'network/qualify.py').write_text('# Synthetic argument fixture only.\n')
        (install / 'network/control.py').write_text('''import pathlib,socket,sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from revisions import TLS_ENFORCEMENT
args=sys.argv[1:]
import json,os
with open(os.environ['FAKE_LOG']+'.control','a') as log: log.write(json.dumps(args)+'\\n')
if args[0]=='snapshot':
 p=pathlib.Path(args[args.index('--session')+1]); (p/'transport').mkdir()
 (p/'config').mkdir(); (p/'logs').mkdir()
 s=socket.socket(socket.AF_UNIX); s.bind(str(p/'transport/proxy.sock')); s.close()
 (p/'transport/ready').write_text('fixture-policy guard='+ 'c'*64 +' mux=1 tls=' + TLS_ENFORCEMENT + '\\n')
 print('fixture-policy')
''')
        return dict(FAKE_NETWORK='1', FAKE_INFO='true linux true',
                    CONTAINER_HOST='unix:///run/service.sock',
                    SANDBOX_CONTAINER_NETWORK='offline')

    def assert_agent_dev_layout(self, create):
        self.assertIn('--read-only', create)
        self.assertNotIn('--read-only-tmpfs=false', create)
        # The engine provides /dev and a devpts that allows pseudo-terminals; an
        # explicit devpts would get ptmxmode=000.
        tmpfs = [create[i + 1] for i, arg in enumerate(create) if arg == '--tmpfs']
        self.assertFalse(any(t == '/dev' or t.startswith('/dev:') or t.startswith('/dev/') for t in tmpfs), tmpfs)
        mounts = [create[i + 1] for i, arg in enumerate(create) if arg == '--mount']
        self.assertFalse(any('type=devpts' in m or m.endswith('destination=/dev') or 'destination=/dev,' in m
                             for m in mounts), mounts)
        self.assertIn('type=tmpfs,destination=/dev/shm,ro=true', mounts)
        self.assertIn('type=tmpfs,destination=/run/secrets,ro=true', mounts)

    def test_shell_state_and_history_location(self):
        for isolated in ('', str(self.state)):
            with self.subTest(isolated=isolated):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(SANDBOX_CONTAINER_STATE_DIR=isolated)
                self.assertEqual(result.returncode, 0, result.stderr)
                environment = self.environment()
                self.assertIn('HOME=/sandbox-home', environment)
                self.assertIn('SANDBOX_CONTAINER_CONFIG_DIR=/sandbox-home/.config/sandbox-container', environment)
                self.assertIn('HISTFILE=/sandbox-home/.config/sandbox-container/bash_history', environment)
                volumes = self.volumes()
                if isolated:
                    self.assertIn(f'{self.state}:/sandbox-home:rw', volumes)
                else:
                    home = Path(self.env['HOME'])
                    self.assertIn(f'{home}/.config/sandbox-container:/sandbox-home/.config/sandbox-container:rw',
                                  volumes)
                    self.assertIn(f'{home}/.config/openspec:/sandbox-home/.config/openspec:rw', volumes)

    def test_symlink_invocation_and_native_permissions(self):
        alias = self.base / 'claude'
        alias.symlink_to(WRAPPER)
        result = subprocess.run([str(alias), '--container-build', '--dangerously-skip-permissions'],
                                cwd=self.project, env=self.env, input='', text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        build = next(c for c in self.calls() if c[0] == 'build')
        self.assertEqual(build[-3:], ['--file', str(ROOT / 'Containerfile'), str(ROOT)])
        self.assertEqual(self.create()[-1], '--dangerously-skip-permissions')

