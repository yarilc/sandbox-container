"""Whether the runner's Podman client gives a --read-only container a read-only /dev.

The guarded terminal tests start a --read-only container with a terminal, as an
interactive session does. Podman provisions a writable /dev tmpfs for it, and
crun replaces /dev/console there to attach the terminal. An older client in the
runtime image (Podman 4.3.1) talking to a Podman 5 server gets a read-only /dev
instead, and crun 1.27 then fails before the test checks anything. The managed
launcher runs with the host's own client and is not affected.

The probe measures that condition directly, once per image, so the terminal
tests skip only where it holds, with a stated reason. A probe that cannot run
raises: it never turns into a skip.
"""
import functools
import subprocess

SKIP_REASON = ("the runner's Podman client gives --read-only containers a read-only /dev on this engine, so no "
               'terminal can attach; check terminal attach with an interactive session instead (AGENTS.md, '
               'Testing Guidelines)')


@functools.lru_cache(maxsize=None)
def read_only_dev(image):
    """True when a --read-only container of image gets a read-only /dev through the runner's client."""
    result = subprocess.run(['podman', 'run', '--rm', '--network=none', '--read-only', '--entrypoint', 'cat', image,
                             '/proc/mounts'], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError('read-only /dev probe failed: ' + result.stdout + result.stderr)
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 4 and fields[1] == '/dev':
            return 'ro' in fields[3].split(',')
    raise RuntimeError('read-only /dev probe found no /dev mount:\n' + result.stdout)
