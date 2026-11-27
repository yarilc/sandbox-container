"""Controlled upstream tests of the dependency mirror HTTP boundary."""

import asyncio
import base64
from contextlib import asynccontextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urljoin
from xml.etree import ElementTree

from sandbox_profile import ROOT  # noqa: F401  (loads the shared network modules from a fixture)
from mirror import (CHUNK, Client, HEADER_LIMIT, MAX_OBJECT, Rejected, forward_response, parse_request, parse_response,
                    rewrite_index, route, upstream_request)
from mirror_cache import Cache
from mirror_policy import profile
from mirror_settings import settings
from policy import PolicyError, resolved_addresses
from proxy import Proxy
import relay


PROFILES = {'rocky': profile({
    'schema': 1, 'name': 'rocky', 'revision': '1', 'default': False,
    'upstreams': [{'id': 'os', 'ecosystem': 'rpm', 'base_url': 'https://repo.test/releases/os/'}],
})}
TARGET = '/mirror/rocky/os/repodata/repomd.xml'


def request(method='GET', target=TARGET, fields=()):
    lines = [f'{method} {target} HTTP/1.1', 'Host: 127.0.0.1:18081', *fields]
    return ('\r\n'.join(lines) + '\r\n\r\n').encode('ascii')


class RequestTests(unittest.TestCase):
    def test_maven_plugin_metadata_and_checksums_use_selected_url(self):
        value = profile(PROFILES['rocky'] | {'name': 'central', 'upstreams': [
            {'id': 'maven', 'ecosystem': 'maven', 'base_url': 'https://repo.test/maven2/'},
        ]})
        profiles = {'central': value}
        prefix = '/mirror/central/maven/'
        for path in ('org/example/plugin/1/plugin-1.jar', 'org/example/plugin/maven-metadata.xml',
                     'org/example/plugin/1/plugin-1.pom.sha1'):
            with self.subTest(path=path):
                self.assertEqual(route(prefix + path, profiles).url, 'https://repo.test/maven2/' + path)
        with self.assertRaises(Rejected):
            route(prefix + 'account/api/credentials', profiles)
        with tempfile.TemporaryDirectory() as root:
            env = settings(Path(root), profiles)
            config = ElementTree.parse(Path(root) / 'maven-settings.xml')
        self.assertIn('maven-settings.xml', env['MAVEN_ARGS'])
        self.assertEqual(config.findtext('./mirrors/mirror/mirrorOf'), '*')
        self.assertEqual(config.findtext('./mirrors/mirror/url'), 'http://127.0.0.1:18081' + prefix)

    def test_pypi_html_and_json_preserve_hashes_and_prune_unknown_origins(self):
        value = profile(PROFILES['rocky'] | {'name': 'python', 'upstreams': [
            {'id': 'index', 'ecosystem': 'pypi', 'base_url': 'https://repo.test/',
             'artifact_bases': [{'base_url': 'https://artifacts.test/packages/'}]},
        ]})
        profiles = {'python': value}
        destination = route('/mirror/python/index/simple/demo/', profiles)
        raw = 'https://artifacts.test/packages/demo-1.0-py3-none-any.whl'
        data = (f'<a href="{raw}#sha256=abc123" data-requires-python="&gt;=3.9">demo.whl</a>'
                '<a href="https://other.test/demo.whl">other</a>').encode()
        rewritten = rewrite_index(data, {}, destination)
        self.assertIn(b'/mirror/python/index/artifacts/1/demo-1.0-py3-none-any.whl#sha256=abc123', rewritten)
        self.assertIn(b'data-requires-python="&gt;=3.9"', rewritten)
        self.assertNotIn(b'other.test', rewritten)
        source = {'meta': {'api-version': '1.0'}, 'files': [{'url': raw, 'hashes': {'sha256': 'abc123'}}]}
        index = json.loads(rewrite_index(json.dumps(source).encode(), {'content-type': 'application/json'}, destination))
        self.assertEqual(index['files'][0]['hashes'], source['files'][0]['hashes'])
        self.assertEqual(route(index['files'][0]['url'], profiles).url, raw)
        with self.assertRaises(Rejected):
            route('/mirror/python/index/artifacts/2/demo.whl', profiles)

    def test_npm_scoped_metadata_and_integrity(self):
        value = profile(PROFILES['rocky'] | {'name': 'javascript', 'upstreams': [
            {'id': 'index', 'ecosystem': 'npm', 'base_url': 'https://repo.test/',
             'artifact_bases': [{'base_url': 'https://files.test/packages/'}]},
        ]})
        profiles = {'javascript': value}
        destination = route('/mirror/javascript/index/@scope%2fdemo', profiles)
        self.assertEqual(destination.url, 'https://repo.test/@scope%2fdemo')
        origin = 'https://files.test/packages/@scope/demo/-/demo-1.0.0.tgz'
        source = {'versions': {'1.0.0': {'dist': {'tarball': origin, 'integrity': 'sha512-fixture'}},
                               '2.0.0': {'dist': {'tarball': 'https://other.test/demo-2.tgz'}}}}
        data = json.loads(rewrite_index(json.dumps(source).encode(), {'content-type': 'application/json'}, destination))
        self.assertEqual(set(data['versions']), {'1.0.0'})
        dist = data['versions']['1.0.0']['dist']
        self.assertEqual(dist['integrity'], 'sha512-fixture')
        self.assertEqual(route(dist['tarball'].removeprefix('http://127.0.0.1:18081'), profiles).url, origin)
        with self.assertRaises(Rejected):
            route('/mirror/javascript/index/-/npm/v1/security/audits', profiles)

    def test_cargo_sparse_config_rewrites_download_and_preserves_index_route(self):
        value = profile(PROFILES['rocky'] | {'name': 'rust', 'upstreams': [
            {'id': 'index', 'ecosystem': 'cargo', 'base_url': 'https://repo.test/sparse/',
             'artifact_bases': [{'base_url': 'https://crates.test/files/'}]},
        ]})
        profiles = {'rust': value}
        prefix = '/mirror/rust/index/'
        self.assertEqual(route(prefix + 'se/rd/serde', profiles).url, 'https://repo.test/sparse/se/rd/serde')
        config = route(prefix + 'config.json', profiles)
        data = rewrite_index(b'{"dl":"https://crates.test/files/{crate}/{crate}-{version}.crate","api":"https://repo.test/write"}',
                             {'content-type': 'application/json'}, config)
        body = json.loads(data)
        self.assertEqual(set(body), {'dl'})
        path = body['dl'].removeprefix('http://127.0.0.1:18081').replace('{crate}', 'serde').replace('{version}', '1.2.3')
        self.assertEqual(route(path, profiles).url, 'https://crates.test/files/serde/serde-1.2.3.crate')
        with self.assertRaises(Rejected):
            route(prefix + 'wrong/serde', profiles)
        with self.assertRaises(Rejected):
            rewrite_index(b'{"dl":"https://elsewhere.test/"}', {}, config)
        with tempfile.TemporaryDirectory() as root:
            settings(Path(root), profiles)
            cargo = (Path(root) / 'cargo.toml').read_text()
        self.assertIn('replace-with = "sandbox-mirror"', cargo)
        self.assertIn('sparse+http://127.0.0.1:18081' + prefix, cargo)

    def test_go_versions_and_checksum_lookups_require_an_approved_module(self):
        value = profile(PROFILES['rocky'] | {'name': 'modules', 'upstreams': [
            {'id': 'proxy', 'ecosystem': 'go', 'base_url': 'https://proxy.test/',
             'module_prefixes': ['example.test/Team']},
        ]})
        profiles = {'modules': value}
        prefix = '/mirror/modules/proxy/'
        for path in ('example.test/!team/demo/@v/list', 'example.test/!team/demo/@v/v1.2.3.zip',
                     'example.test/!team/demo/@latest', 'sumdb/sum.golang.org/supported',
                     'sumdb/sum.golang.org/lookup/example.test/!team/demo@v1.2.3',
                     'sumdb/sum.golang.org/tile/8/0/x001/000.p/8'):
            with self.subTest(path=path):
                self.assertEqual(route(prefix + path, profiles).url, 'https://proxy.test/' + path)
        for path in ('example.test/!teamother/demo/@v/list', 'another.test/!team/@v/list',
                     'sumdb/sum.golang.org/lookup/another.test/demo@v1.2.3',
                     'sumdb/another.test/lookup/example.test/!team/demo@v1.2.3'):
            with self.subTest(path=path), self.assertRaises(Rejected):
                route(prefix + path, profiles)
        with tempfile.TemporaryDirectory() as root:
            values = settings(Path(root), profiles)
        self.assertEqual(values['GOPROXY'], 'http://127.0.0.1:18081' + prefix)
        self.assertEqual(values['GOSUMDB'], 'sum.golang.org')

    def test_invalid_methods_and_body_framing(self):
        for data in (request('POST'), request('CONNECT'), request(fields=('Content-Length: 1',)),
                     request(fields=('Transfer-Encoding: chunked',)),
                     request(fields=('Content-Length: 0', 'Content-Length: 0')),
                     request(fields=('Expect: 100-continue',)), request(fields=('Host: repo.test',)),
                     request(fields=('X: ' + 'a' * HEADER_LIMIT,))):
            with self.subTest(data=data[:80]), self.assertRaises(Rejected):
                parse_request(data)

    def test_paths_remain_inside_the_active_rpm_base(self):
        for path in ('https://repo.test/releases/os/repodata/repomd.xml', '//repo.test/test.rpm',
                     '/mirror/rocky/os/../other.rpm', '/mirror/rocky/os/%2Fother.rpm',
                     '/mirror/rocky/os/repodata/repomd.xml?other=1', '/mirror/other/os/test.rpm',
                     '/mirror/rocky/deleted/test.rpm', '/mirror/rocky/os/repodata/anything.php'):
            with self.subTest(path=path), self.assertRaises(Rejected):
                route(path, PROFILES)
        for path in ('repodata/2ff-primary.xml.gz', 'repodata/repomd.xml.asc', 'Packages/a/abc.rpm'):
            with self.subTest(path=path):
                self.assertEqual(route('/mirror/rocky/os/' + path, PROFILES).url,
                                 'https://repo.test/releases/os/' + path)

    def test_al2023_relative_links_route_to_the_approved_artifact_prefix(self):
        base = '/al2023/core/guids/' + 'a' * 64 + '/x86_64/'
        cdn = 'https://cdn.amazonlinux.com'
        value = {'al2023': profile(PROFILES['rocky'] | {'name': 'al2023', 'upstreams': [
            {'id': 'core', 'ecosystem': 'rpm', 'base_url': cdn + base, 'layout': 'al2023-cdn',
             'artifact_bases': [{'base_url': cdn + '/al2023/blobstore/'}]},
        ]})}
        local = '/mirror/al2023/core'
        artifact = 'b' * 64 + '/fixture-1.0-1.amzn2023.x86_64.rpm'
        normalized = urljoin(local + base, '../../../../blobstore/' + artifact)
        self.assertEqual(normalized, local + '/al2023/blobstore/' + artifact)
        self.assertEqual(route(normalized + '?instance_id=none', value).url, cdn + '/al2023/blobstore/' + artifact)
        for suffix in ('repodata/repomd.xml', 'repodata/repomd.xml.asc', 'repodata/primary.xml.gz'):
            self.assertEqual(route(local + base + suffix, value).url, cdn + base + suffix)
        for denied in (local + '/al2023/blobstore/unapproved.rpm', local + '/al2023/blobstore/index.html',
                       local + base + 'repodata/repomd.xml?instance_id=opaque',
                       local + '/another/blobstore/' + artifact):
            with self.subTest(denied=denied), self.assertRaises(Rejected):
                route(denied, value)

    def test_bounds_and_rejects_ambiguous_upstream_headers(self):
        for fields in (f'Content-Length: {MAX_OBJECT + 1}', 'Content-Length: 1\r\nContent-Length: 1',
                       'Content-Length: 1\r\nTransfer-Encoding: chunked', 'Transfer-Encoding: gzip',
                       'Transfer-Encoding:'):
            with self.subTest(fields=fields), self.assertRaises(Rejected):
                parse_response(f'HTTP/1.1 200 OK\r\n{fields}\r\n\r\n'.encode('ascii'))

    def test_address_scope_checks_all_responses(self):
        def answer(ip):
            return (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', (ip, 443))

        public, private = answer('93.184.216.34'), answer('192.168.2.3')
        for records, scope, allowed in (([public], None, True), ([public, private], None, False),
                                        ([private], ['192.168.2.3'], True),
                                        ([public, private], ['192.168.2.3'], False)):
            with self.subTest(records=records, scope=scope), patch('policy.socket.getaddrinfo', return_value=records):
                if allowed:
                    self.assertEqual(resolved_addresses('repo.test', 443, scope)[0][-1], records[0][-1])
                else:
                    with self.assertRaisesRegex(PolicyError, 'unsafe-address'):
                        resolved_addresses('repo.test', 443, scope)


class UpstreamTests(unittest.IsolatedAsyncioTestCase):
    async def exchange(self, method, reply, target=TARGET, profiles=PROFILES):
        observed = []

        async def serve(reader, writer):
            try:
                observed.append(await reader.readuntil(b'\r\n\r\n'))
                writer.write(reply)
                await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()

        server = await asyncio.start_server(serve, '127.0.0.1', 0, limit=HEADER_LIMIT)
        async with server:
            reader, writer = await asyncio.open_connection('127.0.0.1', server.sockets[0].getsockname()[1],
                                                           limit=HEADER_LIMIT)
            try:
                value = parse_request(request(method, target, fields=('Authorization: dummy', 'Cookie: dummy',
                                                              'X-Api-Key: dummy', 'Accept: application/xml')))
                writer.write(upstream_request(value, route(value.target, profiles)))
                await writer.drain()
                chunks = []

                async def sink(chunk):
                    chunks.append(chunk)

                await forward_response(value, reader, sink)
            finally:
                writer.close()
                await writer.wait_closed()
        return observed[0], b''.join(chunks)

    async def test_only_allowed_fields_reach_upstream(self):
        received, returned = await self.exchange('GET', b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n'
                                                 b'Set-Cookie: dummy\r\n\r\n3\r\nrpm\r\n0\r\n\r\n')
        self.assertEqual(received, b'GET /releases/os/repodata/repomd.xml HTTP/1.1\r\nHost: repo.test\r\n'
                                   b'Connection: close\r\nAccept-Encoding: identity\r\naccept: application/xml\r\n\r\n')
        self.assertEqual(returned, b'HTTP/1.1 200 Mirror response\r\nConnection: close\r\n'
                                   b'Transfer-Encoding: chunked\r\n\r\n3\r\nrpm\r\n0\r\n\r\n')

    async def test_head_returns_no_body(self):
        received, returned = await self.exchange('HEAD', b'HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\n')
        self.assertTrue(received.startswith(b'HEAD '))
        self.assertTrue(returned.endswith(b'Content-Length: 3\r\n\r\n'))

    async def test_cargo_index_and_go_checksum_bytes_pass_through(self):
        for ecosystem, path, suffix, payload, fields in (
            ('cargo', 'se/rd/serde', '/se/rd/serde', b'{"cksum":"fixture"}\n', {}),
            ('go', 'sumdb/sum.golang.org/lookup/example.test/team/demo@v1.2.3',
             '/sumdb/sum.golang.org/lookup/example.test/team/demo@v1.2.3', b'fixture checksum record\n',
             {'module_prefixes': ['example.test/team']}),
        ):
            with self.subTest(ecosystem=ecosystem):
                configured = profile(PROFILES['rocky'] | {'name': 'configured', 'upstreams': [
                    {'id': 'index', 'ecosystem': ecosystem, 'base_url': 'https://repo.test/', **fields},
                ]})
                response = f'HTTP/1.1 200 OK\r\nContent-Length: {len(payload)}\r\n\r\n'.encode() + payload
                received, returned = await self.exchange('GET', response, '/mirror/configured/index/' + path,
                                                          {'configured': configured})
                self.assertTrue(received.startswith(f'GET {suffix} HTTP/1.1\r\n'.encode()))
                self.assertEqual(returned.split(b'\r\n\r\n', 1)[1], payload)


class VerifiedUpstreamTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        asyncio.get_running_loop().set_debug(False)
        if not shutil.which('openssl'):
            self.skipTest('openssl unavailable for the controlled HTTPS fixture')
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.cert = Path(directory.name) / 'cert.pem'
        key = Path(directory.name) / 'key.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256',
                        '-nodes', '-keyout', str(key), '-out', str(self.cert), '-days', '1',
                        '-subj', '/CN=repo.test', '-addext', 'subjectAltName=DNS:repo.test'],
                       capture_output=True, check=True, timeout=10)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.cert, key)
        self.observed = []
        self.redirect = '/releases/os/repodata/actual.xml'
        server = await asyncio.start_server(self.handle, '127.0.0.1', 0, ssl=context)
        self.addAsyncCleanup(server.wait_closed)
        self.addCleanup(server.close)
        self.port = server.sockets[0].getsockname()[1]

    async def handle(self, reader, writer):
        try:
            data = await reader.readuntil(b'\r\n\r\n')
            target = data.split(b' ', 2)[1].decode('ascii')
            self.observed.append(target)
            if target.endswith('/repomd.xml'):
                response = f'HTTP/1.1 302 Moved\r\nLocation: {self.redirect}\r\nContent-Length: 0\r\n\r\n'.encode()
            else:
                index = b'<repomd xmlns="http://linux.duke.edu/metadata/repo"/>'
                response = f'HTTP/1.1 200 OK\r\nContent-Length: {len(index)}\r\n\r\n'.encode() + index
            writer.write(response)
            await writer.drain()
        finally:
            writer.close()

    def resolve(self, host, port, scope):
        self.assertEqual((host, port, scope), ('repo.test', 443, None))
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, ('127.0.0.1', self.port))]

    async def test_verifies_index_and_validates_redirect_again(self):
        client = Client(self.cert, resolver=self.resolve)
        value = PROFILES['rocky']
        await client.verify(value, value['upstreams'][0])
        self.assertEqual(self.observed, ['/releases/os/repodata/repomd.xml', '/releases/os/repodata/actual.xml'])
        self.redirect = '/releases/other/repodata/actual.xml'
        with self.assertRaisesRegex(Rejected, 'redirect-denied'):
            await client.verify(value, value['upstreams'][0])
        self.assertEqual(self.observed[-1], '/releases/os/repodata/repomd.xml')

    async def test_untrusted_certificate_sends_no_http_request(self):
        client = Client(resolver=self.resolve)
        value = PROFILES['rocky']
        with self.assertRaisesRegex(Rejected, 'certificate-rejected'):
            await client.verify(value, value['upstreams'][0])
        self.assertEqual(self.observed, [])


class CacheTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.cache = Cache(directory.name, capacity=4 * CHUNK, object_limit=2 * CHUNK, entries=1)
        self.client = Client()
        self.calls = []
        self.data = b'package'

        @asynccontextmanager
        async def upstream(request, destination):
            self.calls.append((destination.url, request.headers))
            reader = asyncio.StreamReader()
            reader.feed_data(self.data)
            reader.feed_eof()
            yield reader, (200, {}, len(self.data), False)

        self.client.fetch = upstream

    async def transfer(self, suffix, *, profiles=PROFILES, fields=()):
        target = '/mirror/rocky/os/' + suffix
        chunks = []

        async def sink(chunk):
            chunks.append(chunk)

        await self.client.transfer(parse_request(request(target=target, fields=fields)), route(target, profiles),
                                   sink, self.cache)
        return b''.join(chunks)

    async def test_cached_download_is_complete_and_bound_to_policy(self):
        one = await self.transfer('a.rpm')
        self.assertEqual(await self.transfer('a.rpm'), one)
        self.assertEqual(len(self.calls), 1)
        changed = {'rocky': PROFILES['rocky'] | {'revision': '2'}}
        self.data = b'other'
        self.assertTrue((await self.transfer('a.rpm', profiles=changed)).endswith(b'other'))
        self.assertEqual(len(self.cache.entries), 1)
        self.assertEqual(self.cache.used, len(self.data))
        self.assertEqual(len(list(self.cache.directory.glob('object-*'))), 1)

    async def test_indexes_and_ranges_always_reach_upstream(self):
        for _ in range(2):
            await self.transfer('repodata/repomd.xml')
            await self.transfer('a.rpm', fields=('Range: bytes=0-2',))
        self.assertEqual(len(self.calls), 4)
        self.assertFalse(self.cache.entries)

    async def test_oversized_objects_still_stream_and_expired_objects_refetch(self):
        self.data = b'a' * (2 * CHUNK + 1)
        self.assertTrue((await self.transfer('large.rpm')).endswith(self.data))
        self.assertFalse(self.cache.entries)
        self.data = b'ordinary'
        self.cache.ttl = 0
        await self.transfer('a.rpm')
        await self.transfer('a.rpm')
        self.assertEqual(len(self.calls), 3)

    async def test_cancelled_transfer_removes_partial_and_releases_reservation(self):
        self.data = b'a' * (CHUNK + 1)
        started = asyncio.Event()

        async def sink(chunk):
            if len(chunk) == CHUNK:
                started.set()
                await asyncio.Event().wait()

        request_value = parse_request(request(target='/mirror/rocky/os/a.rpm'))
        task = asyncio.create_task(self.client.transfer(request_value, route(request_value.target, PROFILES),
                                                        sink, self.cache))
        await asyncio.wait_for(started.wait(), 2)
        await self.transfer('a.rpm')
        self.assertFalse(self.cache.entries)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.cache.used, 0)
        self.assertFalse(list(self.cache.directory.iterdir()))


class ConfinedTransportTests(unittest.IsolatedAsyncioTestCase):
    @unittest.skipUnless(shutil.which('npm'), 'npm client unavailable')
    async def test_npm_install_uses_rewritten_tarball_in_a_fresh_cache(self):
        asyncio.get_running_loop().set_debug(False)
        package = {'name': '@scope/demo', 'version': '1.0.0'}
        content = json.dumps(package).encode()
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode='w:gz') as archive:
            item = tarfile.TarInfo('package/package.json')
            item.size = len(content)
            archive.addfile(item, io.BytesIO(content))
        tarball = output.getvalue()
        integrity = 'sha512-' + base64.b64encode(hashlib.sha512(tarball).digest()).decode()
        artifact = 'https://files.test/packages/@scope/demo/-/demo-1.0.0.tgz'
        packument = package | {'dist-tags': {'latest': '1.0.0'}, 'versions': {
            '1.0.0': package | {'dist': {'tarball': artifact, 'integrity': integrity}},
        }}
        selected = profile(PROFILES['rocky'] | {'name': 'javascript', 'upstreams': [
            {'id': 'npm', 'ecosystem': 'npm', 'base_url': 'https://repo.test/',
             'artifact_bases': [{'base_url': 'https://files.test/packages/'}]},
        ]})
        fixture = Client()
        seen = []

        @asynccontextmanager
        async def fetch(value, destination):
            seen.append(destination.url)
            payload = tarball if destination.url == artifact else json.dumps(packument).encode()
            reader = asyncio.StreamReader()
            reader.feed_data(payload)
            reader.feed_eof()
            yield reader, (200, {'content-type': 'application/gzip' if destination.url == artifact
                                else 'application/json'}, len(payload), False)

        fixture.fetch = fetch
        from proxy import Audit
        with tempfile.TemporaryDirectory(prefix='mirror-npm-') as directory:
            root = Path(directory)
            trusted = Proxy(None, Audit(root / 'denials.jsonl', 'npm-fixture'),
                            mirror_profiles={'javascript': selected}, mirror_client=fixture)
            left, right = socket.socketpair()
            left.setblocking(False)
            right.setblocking(False)
            reader, writer = await asyncio.open_connection(sock=right)
            peer = asyncio.create_task(trusted.handle(reader, writer))
            read_ready, write_ready = os.pipe()
            adapter = asyncio.create_task(relay.run(left, write_ready, provider=False, dependency=True))
            try:
                self.assertEqual(await asyncio.wait_for(asyncio.to_thread(os.read, read_ready, 1), 3), b'1')
                env = dict(PATH=os.environ['PATH'], HOME=directory, NO_PROXY='127.0.0.1')
                result = await asyncio.to_thread(subprocess.run, [
                    'npm', 'install', '--ignore-scripts', '--no-audit', '--no-fund', '--no-package-lock', '--fetch-retries=0',
                    '--registry=http://127.0.0.1:18081/mirror/javascript/npm/', '--cache', str(root / 'cache'), '@scope/demo'],
                    cwd=directory, env=env, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads((root / 'node_modules/@scope/demo/package.json').read_text()), package)
                self.assertIn(artifact, seen)
            finally:
                os.close(read_ready)
                writer.close()
                adapter.cancel()
                await asyncio.gather(peer, adapter, return_exceptions=True)

    async def test_trusted_mirror_transport_authorizes_and_drains_the_response(self):
        asyncio.get_running_loop().set_debug(False)
        observed = []
        length = 300_000

        class Upstream:
            async def transfer(self, value, destination, sink, cache):
                observed.append((value.method, destination.url, value.headers))
                await sink(f'HTTP/1.1 200 OK\r\nContent-Length: {length}\r\n\r\n'.encode())
                await sink(b'a' * length)

        class Audit:
            def record(self, *_):
                pass

        proxy = Proxy(None, Audit(), mirror_profiles=PROFILES, mirror_client=Upstream())
        left, right = socket.socketpair()
        left.setblocking(False)
        right.setblocking(False)
        peer_reader, peer_writer = await asyncio.open_connection(sock=right)
        peer = asyncio.create_task(proxy.handle(peer_reader, peer_writer))
        ready_read, ready_write = os.pipe()
        self.addCleanup(os.close, ready_read)
        start_server = asyncio.start_server
        addresses = []

        async def ephemeral(handler, host, port, **kwargs):
            self.assertEqual((host, port), ('127.0.0.1', 18081))
            listener = await start_server(handler, host, 0, **kwargs)
            addresses.append(listener.sockets[0].getsockname())
            return listener

        with patch.object(relay.asyncio, 'start_server', ephemeral):
            running = asyncio.create_task(relay.run(left, ready_write, provider=False, dependency=True))
            try:
                self.assertEqual(await asyncio.wait_for(asyncio.to_thread(os.read, ready_read, 1), 2), b'1')
                for method in ('POST', 'GET'):
                    reader, writer = await asyncio.open_connection(*addresses[0])
                    try:
                        writer.write(request(method, fields=('Authorization: fixture', 'Cookie: fixture')))
                        await writer.drain()
                        response = await asyncio.wait_for(reader.read(), 5)
                        if method == 'POST':
                            self.assertTrue(response.startswith(b'HTTP/1.1 403'))
                        else:
                            self.assertEqual(response.split(b'\r\n\r\n', 1)[1], b'a' * length)
                    finally:
                        writer.close()
                self.assertEqual(observed, [('GET', 'https://repo.test/releases/os/repodata/repomd.xml', {})])
                peer_writer.close()
                await asyncio.wait_for(running, 3)
                with self.assertRaises(ConnectionRefusedError):
                    await asyncio.open_connection(*addresses[0])
            finally:
                peer_writer.close()
                running.cancel()
                await asyncio.gather(running, peer, return_exceptions=True)
