#!/usr/bin/env python3
"""Reference-only provider session harness for the network runtime tests.

The reference profile declares no authentication method, so the reference
wrapper has no provider mode. This harness drives the shared session helper
(``prepare``, ``start``, ``agent-args``, ``stop``) from a protected fixture
installation with the agent-neutral fixture profile, and runs the real runtime
image with the production guard, relay and proxy. It reproduces only the
container options a wrapper adds around ``agent-args``; wrapper lifecycle
(naming, recovery, signal forwarding) stays covered by each agent wrapper.

Usage: provider_session.py [command...]   (stdin is forwarded; cwd is the workspace)
Environment: PROVIDER_INSTALL, PROVIDER_RUNTIME, PROVIDER_IMAGE, PROVIDER_POLICY,
PROVIDER_PROFILE, PROVIDER_PROXY_IMAGE, optional PROVIDER_CA, CONTAINER_HOST.
"""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile

HOME = '/sandbox-home'
CA = HOME + '/ca/bundle.pem'


def run(command, **kwargs):
    result = subprocess.run([str(part) for part in command], **kwargs)
    if result.returncode:
        sys.exit(result.returncode)
    return result


def query(*args):
    return run(['podman', *args], stdout=subprocess.PIPE, text=True).stdout.rstrip('\n')


def interrupted(signum, frame):
    raise SystemExit(128 + signum)


def main():
    install = Path(os.environ['PROVIDER_INSTALL'])
    runtime = Path(os.environ['PROVIDER_RUNTIME'])
    workspace = Path.cwd().resolve()
    command = sys.argv[1:] or ['/bin/bash']
    helper = [sys.executable, '-I', install / 'network/session.py']
    network = ['--installation', install, '--writable', workspace, '--mount-target', workspace,
               '--policy', os.environ['PROVIDER_POLICY'], '--profile', os.environ['PROVIDER_PROFILE'],
               '--proxy-image', os.environ['PROVIDER_PROXY_IMAGE'], '--runtime', runtime]
    platform = query('info', '--format', '{{json .Host}}')
    prepared = run([*helper, 'prepare', *network, '--mode', 'provider',
                    '--server-version', query('version', '--format', '{{.Server.Version}}'),
                    '--backend', query('info', '--format', '{{.Host.NetworkBackend}}'),
                    '--endpoint', os.environ.get('CONTAINER_HOST', ''), '--engine', 'true linux true'],
                   input=platform, stdout=subprocess.PIPE, text=True)
    digest = prepared.stdout.split()[0]
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, interrupted)
    session = Path(tempfile.mkdtemp(prefix='session.', dir=runtime))
    status = 1
    try:
        run([*helper, 'start', *network, '--session', session, '--guard-digest', digest], stdout=subprocess.PIPE)
        records = run([*helper, 'agent-args', '--installation', install, '--mode', 'provider',
                       '--session', session, '--guard-digest', digest, '--', *command],
                      stdout=subprocess.PIPE).stdout.split(b'\0')[:-1]
        count = int(records[0])
        options = [record.decode() for record in records[1:1 + count]]
        entry = [record.decode() for record in records[1 + count:]]
        arguments = ['podman', 'run', '--rm', '--interactive', '--read-only',
                     '--userns=keep-id', '--user', f'{os.getuid()}:{os.getgid()}',
                     '--cap-drop=all', '--security-opt=no-new-privileges', '--workdir', str(workspace),
                     '--tmpfs', '/tmp:rw,nosuid,nodev,noexec,size=256m,mode=1777',
                     '--tmpfs', '/run:rw,nosuid,nodev,noexec,size=16m',
                     '--tmpfs', '/var/tmp:rw,nosuid,nodev,noexec,size=256m,mode=1777',
                     '--mount', 'type=tmpfs,destination=/run/secrets,ro=true',
                     '--mount', 'type=tmpfs,destination=/dev/shm,ro=true',
                     '--env', 'HOME=' + HOME, '--volume', f'{workspace}:{workspace}:rw']
        if os.environ.get('PROVIDER_CA'):
            arguments += ['--volume', f'{os.environ["PROVIDER_CA"]}:{CA}:ro']
            for variable in ('SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE', 'NODE_EXTRA_CA_CERTS'):
                arguments += ['--env', f'{variable}={CA}']
        arguments += [*options, os.environ['PROVIDER_IMAGE'], *entry]
        status = subprocess.run(arguments).returncode
    finally:
        subprocess.run([str(part) for part in (*helper, 'stop', '--session', session, '--deadline', '20')])
        shutil.rmtree(session, ignore_errors=True)
    sys.exit(status)


if __name__ == '__main__':
    main()
