"""Exercise real DNF clients through the production relay and trusted mirror code."""

import argparse
import asyncio
import contextlib
import gzip
import hashlib
import json
import os
from pathlib import Path
import socket
import ssl
import shutil
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'network'))
from mirror import Client  # noqa: E402
from proxy import Audit, Proxy  # noqa: E402
import relay  # noqa: E402

ROCKY = 'docker.io/rockylinux/rockylinux@sha256:99cbe0f114cc4a71cca40a014d690251bb13df65ebc3fb06ff6ec1037e0e1086'
AMAZON = 'localhost/al2023-systemd:1.0.0'
BASE_URL = 'http://127.0.0.1:18081/mirror/fixture/rpm/'
REPO = 'sandbox-mirror-test'


def repository():
    root = 'http://linux.duke.edu/metadata/'
    index = [f'<repomd xmlns="{root}repo">']
    result = {}
    for kind, tag, namespace in (('primary', 'metadata', 'common'), ('filelists', 'filelists', 'filelists')):
        raw = f'<{tag} xmlns="{root}{namespace}" packages="0"/>'.encode()
        zipped = gzip.compress(raw, mtime=0)
        filename = f'repodata/{kind}.xml.gz'
        result[filename] = zipped
        index.append(f'<data type="{kind}"><checksum type="sha256">{hashlib.sha256(zipped).hexdigest()}</checksum>'
                     f'<open-checksum type="sha256">{hashlib.sha256(raw).hexdigest()}</open-checksum>'
                     f'<location href="{filename}"/><timestamp>1</timestamp><size>{len(zipped)}</size>'
                     f'<open-size>{len(raw)}</open-size></data>')
    result['repodata/repomd.xml'] = ('\n'.join(index) + '\n</repomd>').encode()
    return result


async def command(*args, timeout=50, check=True):
    return await asyncio.to_thread(subprocess.run, args, capture_output=True, text=True, timeout=timeout, check=check)


async def makecache(images, directory, seen, signed=None):
    flags = ['-y', '--disablerepo=*', f'--repofrompath={REPO},{BASE_URL}', f'--enablerepo={REPO}',
             f'--setopt={REPO}.skip_if_unavailable=false', f'--setopt={REPO}.timeout=2',
             f'--setopt={REPO}.retries=1', f'--setopt={REPO}.gpgcheck=1', '--refresh']
    if signed:
        flags.extend((f'--setopt={REPO}.repo_gpgcheck=1', f'--setopt={REPO}.gpgkey=file:///fixture-key.asc'))
    for image in images:
        suffix = uuid.uuid4().hex
        name = 'sandbox-mirror-rpm-' + suffix
        tag = 'localhost/sandbox-mirror-rpm:' + suffix
        try:
            await command('podman', 'run', '--detach', '--pull=never', '--systemd=always', '--network=host',
                          '--name', name, '--entrypoint', '/sbin/init', image)
            if signed:
                await command('podman', 'cp', str(signed.repo / 'fixture-key.asc'), name + ':/fixture-key.asc')
            before = len(seen)
            result = await command('podman', 'exec', name, 'dnf', *flags, 'makecache')
            if 'Metadata cache created' not in result.stdout or len(seen) <= before:
                raise RuntimeError(f'DNF did not refresh the controlled repository in {image}: {result.stdout}')
            print(f'DNF nested systemd refresh passed for {image}', flush=True)
            result = await command('podman', 'run', '--rm', '--pull=never', '--network=none',
                                   '--entrypoint', '/usr/bin/dnf', image, *flags, 'makecache', check=False)
            if result.returncode == 0 or 'Failed to download metadata' not in result.stderr:
                raise RuntimeError(f'DNF did not report an isolated mirror failure in {image}: {result.stderr}')
            context = directory / suffix
            context.mkdir()
            steps = ['FROM ' + image]
            if signed:
                absent = await command('podman', 'exec', name, 'rpm', '-q', signed.package, check=False)
                if absent.returncode == 0:
                    raise RuntimeError('signed fixture package was already in the target image')
                await command('podman', 'exec', name, 'dnf', *flags, 'install', signed.package)
                await command('podman', 'exec', name, 'rpm', '-q', signed.package)
                await command('podman', 'exec', name, 'systemctl', 'start', signed.unit)
                await command('podman', 'exec', name, 'systemctl', 'is-active', signed.unit)
                journal = await command('podman', 'exec', name, 'journalctl', '--no-pager', '-u', signed.unit)
                if 'sandbox-mirror-fixture' not in journal.stdout:
                    raise RuntimeError('installed unit did not write the fixture journal marker')
                shutil.copyfile(signed.repo / 'fixture-key.asc', context / 'fixture-key.asc')
                steps.extend(('COPY fixture-key.asc /fixture-key.asc',
                              'RUN ' + json.dumps(['dnf', *flags, 'install', signed.package])))
            else:
                steps.append('RUN ' + json.dumps(['dnf', *flags, 'makecache']))
            (context / 'Containerfile').write_text('\n'.join(steps) + '\n')
            before = len(seen)
            await command('podman', 'build', '--pull=never', '--no-cache', '--layers=false',
                          '--network=host', '--tag', tag, str(context))
            if len(seen) <= before:
                raise RuntimeError(f'Build did not fetch the controlled repository in {image}')
            print(f'DNF build refresh and network isolation passed for {image}', flush=True)
        finally:
            await command('podman', 'rm', '--force', '--time', '1', '--ignore', name, check=False)
            await command('podman', 'image', 'rm', tag, check=False)


async def run(images, signed=None):
    for image in images:
        await command('podman', 'image', 'exists', image)
    with tempfile.TemporaryDirectory(prefix='mirror-rpm-') as path:
        directory = Path(path)
        key, cert = directory / 'key.pem', directory / 'cert.pem'
        await command('openssl', 'req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256',
                      '-nodes', '-days', '1', '-subj', '/CN=rpm-fixture.test',
                      '-addext', 'subjectAltName=DNS:rpm-fixture.test', '-keyout', str(key), '-out', str(cert))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        files = {} if signed else repository()
        seen = []

        async def handle(reader, writer):
            try:
                request = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 3)
                target = request.split(b' ', 2)[1].decode('ascii')
                seen.append(target)
                suffix = target.removeprefix('/rpm/')
                body = files.get(suffix, b'')
                if signed:
                    path = (signed.repo / suffix).resolve()
                    if path.is_relative_to(signed.repo) and path.is_file() and path.stat().st_size <= 16 << 20:
                        body = path.read_bytes()
                status = '200 OK' if body else '404 Missing'
                writer.write(f'HTTP/1.1 {status}\r\nContent-Length: {len(body)}\r\n\r\n'.encode() + body)
                await writer.drain()
            finally:
                writer.close()

        upstream = await asyncio.start_server(handle, '127.0.0.1', 0, ssl=context)
        port = upstream.sockets[0].getsockname()[1]

        def resolver(host, requested_port, scope):
            if (host, requested_port, scope) != ('rpm-fixture.test', 443, None):
                raise ValueError('unexpected RPM fixture destination')
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, ('127.0.0.1', port))]

        profile = {'fixture': {'schema': 1, 'name': 'fixture', 'revision': '1', 'default': False, 'upstreams': [
            {'id': 'rpm', 'ecosystem': 'rpm', 'base_url': 'https://rpm-fixture.test/rpm/'},
        ]}}
        trusted = Proxy(None, Audit(directory / 'denials.jsonl', 'rpm-fixture'), mirror_profiles=profile,
                        mirror_client=Client(cert, resolver=resolver))
        left, right = socket.socketpair()
        left.setblocking(False)
        right.setblocking(False)
        reader, writer = await asyncio.open_connection(sock=right)
        peer = asyncio.create_task(trusted.handle(reader, writer))
        read_ready, write_ready = os.pipe()
        adapter = asyncio.create_task(relay.run(left, write_ready, provider=False, dependency=True))
        try:
            async with upstream:
                if await asyncio.wait_for(asyncio.to_thread(os.read, read_ready, 1), 5) != b'1':
                    raise RuntimeError('mirror fixture did not start')
                await makecache(images, directory, seen, signed)
        finally:
            os.close(read_ready)
            writer.close()
            adapter.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await adapter
            await peer


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('images', nargs='*')
    parser.add_argument('--repo', type=lambda path: Path(path).resolve())
    parser.add_argument('--package')
    parser.add_argument('--unit')
    args = parser.parse_args()
    if any((args.repo, args.package, args.unit)) and not all((args.repo, args.package, args.unit)):
        parser.error('signed fixtures require --repo, --package and --unit together')
    try:
        asyncio.run(run(args.images or (ROCKY, AMAZON), args if args.repo else None))
    except subprocess.CalledProcessError as error:
        sys.exit(error.stdout + error.stderr)
