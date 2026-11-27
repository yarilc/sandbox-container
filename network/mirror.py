"""Read-only HTTP vocabulary used by the trusted dependency mirror."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
import json
import re
import socket
import ssl
from urllib.parse import unquote, urljoin, urlsplit
from xml.etree import ElementTree

from mirror_policy import SEGMENT, is_name
from policy import PolicyError, resolved_addresses, revision
import mirror_metadata

HEADER_LIMIT = 8192
MAX_OBJECT = 4 << 30
MAX_INDEX = 4 << 20
CHUNK = 16 * 1024
HEADER_TIMEOUT = 10
TOKEN = re.compile(r"[A-Za-z0-9!#$%&'*+.^_`|~-]+")
NUMBER = re.compile(r'[0-9]{1,12}')
RANGE = re.compile(r'bytes=(?:[0-9]{1,12}-[0-9]{0,12}|-[0-9]{1,12})')
RPM_METADATA = re.compile(r'.+\.(?:xml|gz|bz2|xz|zst|zck|sqlite|yaml|asc)')
MAVEN_INDEX = re.compile(r'maven-metadata(?:-[A-Za-z0-9._-]+)?\.xml(?:\.(?:asc|md5|sha1|sha256|sha512))*')
NPM_NAME = re.compile(r'[a-z0-9][a-z0-9._-]{0,213}')
NPM_SCOPE = re.compile(r'@[a-z0-9][a-z0-9._-]{0,212}')
CRATE = re.compile(r'[a-z0-9][a-z0-9_-]{0,63}')
GO_SEGMENT = re.compile(r'[A-Za-z0-9._+~!@-]+')
GO_MODULE_SEGMENT = re.compile(r'(?:[a-z0-9._+~-]|![a-z])+')
GO_VERSION = re.compile(r'(?:[A-Za-z0-9._+~-]|![a-z])+')
READ_HEADERS = frozenset(('accept', 'if-modified-since', 'if-none-match', 'range', 'if-range'))
RESPONSE_HEADERS = frozenset(('cache-control', 'content-encoding', 'content-range', 'content-type',
                             'etag', 'last-modified', 'accept-ranges'))
FRAMING_HEADERS = frozenset(('content-length', 'transfer-encoding', 'host', 'connection', 'upgrade'))
LOCAL_AUTHORITY = '127.0.0.1:18081'
REDIRECTS = frozenset((301, 302, 303, 307, 308))
INDEX_PATHS = {'rpm': 'repodata/repomd.xml', 'maven': 'org/apache/maven/maven-core/maven-metadata.xml',
               'pypi': 'simple/pip/', 'npm': 'npm', 'cargo': 'config.json'}


class Rejected(ValueError):
    """Failure messages are fixed reason codes suitable for a protected audit."""


@dataclass(frozen=True)
class Request:
    method: str
    target: str
    headers: dict


@dataclass(frozen=True)
class Route:
    profile: str
    revision: str
    upstream: dict
    suffix: str

    @property
    def url(self):
        return self.upstream['base_url'] + self.suffix


def header_lines(data):
    if len(data) > HEADER_LIMIT or not data.endswith(b'\r\n\r\n'):
        raise Rejected('invalid-header-block')
    try:
        first, *lines = data[:-4].decode('ascii').split('\r\n')
    except UnicodeDecodeError:
        raise Rejected('invalid-header-block') from None
    headers = {}
    for line in lines:
        name, separator, value = line.partition(':')
        if not separator or not TOKEN.fullmatch(name) or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise Rejected('invalid-header-field')
        key = name.lower()
        if key in headers:
            if key in FRAMING_HEADERS or key == 'location':
                raise Rejected('ambiguous-header-field')
            continue
        headers[key] = value.strip(' ')
    return first, headers


def parse_request(data):
    first, headers = header_lines(data)
    words = first.split(' ')
    if len(words) != 3 or words[0] not in ('GET', 'HEAD') or words[2] not in ('HTTP/1.0', 'HTTP/1.1'):
        raise Rejected('invalid-request-line')
    if headers.get('host', '') != LOCAL_AUTHORITY and (words[2] == 'HTTP/1.1' or 'host' in headers):
        raise Rejected('invalid-request-authority')
    if ('transfer-encoding' in headers or headers.get('content-length', '0') != '0'
            or {'upgrade', 'expect', 'trailer'} & headers.keys()):
        raise Rejected('unsupported-request-framing')
    nominated = {part.strip().lower() for part in headers.get('connection', '').split(',')}
    safe_headers = {key: value for key, value in headers.items() if key in READ_HEADERS and key not in nominated}
    if 'range' in safe_headers and not RANGE.fullmatch(safe_headers['range']):
        raise Rejected('invalid-range')
    return Request(words[0], words[1], safe_headers)


def clean_segments(path, alphabet=SEGMENT):
    if not path.startswith('/') or path.startswith('//') or len(path) > 4096:
        raise Rejected('invalid-request-target')
    segments = path[1:].split('/')
    if any(segment in ('.', '..') or not alphabet.fullmatch(segment) for segment in segments):
        raise Rejected('invalid-request-target')
    return segments


def rpm_route(parts):
    if len(parts) == 2 and parts[0] == 'repodata' and RPM_METADATA.fullmatch(parts[1]):
        return '/'.join(parts)
    if parts and parts[-1].endswith('.rpm'):
        return '/'.join(parts)
    raise Rejected('rpm-route-denied')


def rpm_artifact(parts, layout):
    if parts and parts[-1].endswith('.rpm') and (
            layout != 'al2023-cdn' or len(parts) == 2 and re.fullmatch('[a-f0-9]{64}', parts[0])):
        return '/'.join(parts)
    raise Rejected('rpm-artifact-route-denied')


def maven_route(parts):
    if len(parts) >= 2 and MAVEN_INDEX.fullmatch(parts[-1]):
        return '/'.join(parts)
    if len(parts) >= 4:
        artifact, version, filename = parts[-3:]
        prefix = artifact + '-' + version.removesuffix('SNAPSHOT') if version.endswith('-SNAPSHOT') else artifact + '-' + version
        if filename.startswith(prefix) and filename[len(prefix):] and '.' in filename[len(prefix):]:
            return '/'.join(parts)
    raise Rejected('maven-route-denied')


def pypi_route(parts):
    value = '/'.join(parts)
    if mirror_metadata.python_index(value):
        return value
    raise Rejected('pypi-route-denied')


def npm_route(parts):
    if len(parts) == 1 and NPM_NAME.fullmatch(parts[0]):
        return parts[0]
    if len(parts) == 2 and NPM_SCOPE.fullmatch(parts[0]) and NPM_NAME.fullmatch(parts[1]):
        return '%2f'.join(parts)
    if len(parts) in (3, 4) and parts[-2] == '-' and parts[-1].endswith('.tgz'):
        npm_route(parts[:-2])
        return '/'.join(parts)
    raise Rejected('npm-route-denied')


def cargo_route(parts):
    if parts == ['config.json']:
        return 'config.json'
    name = parts[-1]
    if not CRATE.fullmatch(name):
        raise Rejected('cargo-route-denied')
    if len(name) < 3:
        expected = [str(len(name)), name]
    elif len(name) == 3:
        expected = ['3', name[0], name]
    else:
        expected = [name[:2], name[2:4], name]
    if parts != expected:
        raise Rejected('cargo-route-denied')
    return '/'.join(parts)


def go_module(parts, upstream):
    if not parts or not all(GO_MODULE_SEGMENT.fullmatch(part) for part in parts):
        raise Rejected('go-module-denied')
    module = re.sub(r'!([a-z])', lambda match: match[1].upper(), '/'.join(parts))
    if not any(module == prefix or module.startswith(prefix + '/') for prefix in upstream['module_prefixes']):
        raise Rejected('go-module-denied')


def go_route(parts, upstream):
    if parts[:2] == ['sumdb', 'sum.golang.org']:
        action = parts[2:]
        if action in (['supported'], ['latest']):
            return '/'.join(parts)
        if len(action) >= 2 and action[0] == 'lookup':
            module, separator, version = action[-1].rpartition('@')
            if separator and GO_VERSION.fullmatch(version):
                go_module([*action[1:-1], module], upstream)
                return '/'.join(parts)
        if (len(action) >= 4 and action[0] == 'tile' and re.fullmatch('[0-9]{1,2}', action[1])
                and re.fullmatch(r'(?:[0-9]{1,2}|data)', action[2])
                and all(re.fullmatch(r'x?[0-9]{1,6}(?:\.p)?', tile) for tile in action[3:])):
            return '/'.join(parts)
        raise Rejected('go-checksum-route-denied')
    if parts[-1] == '@latest':
        go_module(parts[:-1], upstream)
        return '/'.join(parts)
    if len(parts) < 3 or parts[-2] != '@v':
        raise Rejected('go-route-denied')
    go_module(parts[:-2], upstream)
    name, dot, extension = parts[-1].rpartition('.')
    if parts[-1] == 'list' or (dot and extension in ('info', 'mod', 'zip') and GO_VERSION.fullmatch(name)):
        return '/'.join(parts)
    raise Rejected('go-route-denied')


ROUTES = {'rpm': rpm_route, 'maven': maven_route, 'pypi': pypi_route, 'npm': npm_route, 'cargo': cargo_route}


def primary_path(upstream, parts):
    ecosystem = upstream['ecosystem']
    return go_route(parts, upstream) if ecosystem == 'go' else ROUTES[ecosystem](parts)


def route_parts(raw, ecosystem):
    if ecosystem == 'go':
        return clean_segments('/' + raw, GO_SEGMENT)
    if ecosystem == 'npm' and raw.startswith('@'):
        raw = re.sub(r'%2[fF]', '/', raw, count=1)
        scope, separator, rest = raw.partition('/')
        if separator and NPM_SCOPE.fullmatch(scope):
            return [scope, *clean_segments('/' + rest)]
    if ecosystem == 'pypi' and raw.endswith('/'):
        return [*clean_segments('/' + raw[:-1]), '']
    return clean_segments('/' + raw)


def artifact_scope(upstream, number):
    sources = [upstream, *upstream.get('artifact_bases', ())]
    if number >= len(sources):
        raise Rejected('artifact-prefix-denied')
    origin = sources[number]
    return {**upstream, 'base_url': origin['base_url'], 'addresses': origin.get('addresses'), 'artifact': True}


def artifact_path(ecosystem, parts):
    if ecosystem == 'pypi' and parts and mirror_metadata.PYTHON_FILE.fullmatch(parts[-1]):
        return '/'.join(parts)
    if ecosystem == 'npm' and parts and parts[-1].endswith('.tgz'):
        return '/'.join(parts)
    if ecosystem == 'cargo' and parts and (parts[-1].endswith('.crate') or (
            len(parts) >= 3 and parts[-1] == 'download' and CRATE.fullmatch(parts[-3]))):
        return '/'.join(parts)
    raise Rejected('artifact-route-denied')


def route(target, profiles):
    path, query, options = target.partition('?')
    parts = path.split('/', 4)
    if len(target) > 4096 or len(parts) != 5 or parts[:2] != ['', 'mirror'] or not all(map(is_name, parts[2:4])):
        raise Rejected('mirror-route-denied')
    _, _, name, upstream_id, raw = parts
    if name not in profiles:
        raise Rejected('mirror-profile-unavailable')
    profile = profiles[name]
    for upstream in profile['upstreams']:
        if upstream['id'] == upstream_id:
            if query and (upstream.get('layout') != 'al2023-cdn' or options != 'instance_id=none'):
                raise Rejected('mirror-query-denied')
            identity = revision(profile)
            ecosystem = upstream['ecosystem']
            if ecosystem in ('pypi', 'npm', 'cargo') and raw.startswith('artifacts/'):
                _, separator, value = raw.partition('/')
                number, delimiter, suffix = value.partition('/')
                if not separator or not delimiter or not re.fullmatch('[0-8]', number):
                    raise Rejected('artifact-prefix-denied')
                origin = artifact_scope(upstream, int(number))
                return Route(name, identity, origin, artifact_path(ecosystem, route_parts(suffix, ecosystem)))
            suffix = route_parts(raw, ecosystem)
            if upstream['ecosystem'] == 'rpm' and upstream.get('artifact_bases'):
                return split_rpm_route(name, identity, upstream, suffix)
            return Route(name, identity, upstream, primary_path(upstream, suffix))
    raise Rejected('mirror-upstream-unavailable')


def split_rpm_route(name, identity, upstream, parts):
    path = '/'.join(parts)
    metadata = urlsplit(upstream['base_url']).path.lstrip('/')
    if path.startswith(metadata):
        return Route(name, identity, upstream, rpm_route(path[len(metadata):].split('/')))
    for origin in upstream['artifact_bases']:
        prefix = urlsplit(origin['base_url']).path.lstrip('/')
        if path.startswith(prefix):
            suffix = rpm_artifact(path[len(prefix):].split('/'), upstream.get('layout'))
            actual = {**upstream, 'base_url': origin['base_url'], 'addresses': origin.get('addresses'), 'artifact': True}
            return Route(name, identity, actual, suffix)
    raise Rejected('rpm-prefix-denied')


def upstream_request(request, destination):
    url = urlsplit(destination.url)
    fields = [f'{request.method} {url.path} HTTP/1.1', f'Host: {url.netloc}',
              'Connection: close', 'Accept-Encoding: identity']
    fields.extend(f'{key}: {value}' for key, value in request.headers.items())
    return ('\r\n'.join(fields) + '\r\n\r\n').encode('ascii')


async def read_head(reader):
    try:
        return await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), HEADER_TIMEOUT)
    except (asyncio.LimitOverrunError, asyncio.IncompleteReadError, asyncio.TimeoutError):
        raise Rejected('incomplete-http-header') from None


def parse_response(data):
    first, headers = header_lines(data)
    words = first.split(' ', 2)
    if len(words) < 2 or words[0] not in ('HTTP/1.0', 'HTTP/1.1') or not re.fullmatch('[2345][0-9]{2}', words[1]):
        raise Rejected('invalid-upstream-status')
    transfer = headers.get('transfer-encoding')
    length = headers.get('content-length')
    if transfer is not None and (transfer.lower() != 'chunked' or length is not None):
        raise Rejected('unsupported-upstream-framing')
    if length is not None and (not NUMBER.fullmatch(length) or int(length) > MAX_OBJECT):
        raise Rejected('upstream-object-too-large')
    return int(words[1]), headers, int(length) if length is not None else None, transfer is not None


async def body_chunks(reader, length, chunked):
    if chunked:
        total = 0
        while True:
            size = (await reader.readuntil(b'\r\n'))[:-2].split(b';', 1)[0]
            if not re.fullmatch(rb'[a-fA-F0-9]{1,12}', size):
                raise Rejected('invalid-upstream-chunk')
            count = int(size, 16)
            if not count:
                remaining = HEADER_LIMIT
                while line := await reader.readuntil(b'\r\n'):
                    if line == b'\r\n':
                        break
                    remaining -= len(line)
                    if remaining <= 0:
                        raise Rejected('invalid-upstream-trailer')
                return
            total += count
            if total > MAX_OBJECT:
                raise Rejected('upstream-object-too-large')
            while count:
                data = await reader.readexactly(min(count, CHUNK))
                yield data
                count -= len(data)
            if await reader.readexactly(2) != b'\r\n':
                raise Rejected('invalid-upstream-chunk')
    elif length is not None:
        while length:
            data = await reader.readexactly(min(length, CHUNK))
            yield data
            length -= len(data)
    else:
        total = 0
        while data := await reader.read(CHUNK):
            total += len(data)
            if total > MAX_OBJECT:
                raise Rejected('upstream-object-too-large')
            yield data


def response_head(response, *, chunked=False):
    status, headers, length, _ = response
    if 300 <= status < 400 and status != 304:
        raise Rejected('upstream-redirect-denied')
    copied = [f'{key}: {value}' for key, value in headers.items() if key in RESPONSE_HEADERS]
    lines = [f'HTTP/1.1 {status} Mirror response', 'Connection: close', *copied]
    if length is not None and status != 204:
        lines.append(f'Content-Length: {length}')
    if chunked:
        lines.append('Transfer-Encoding: chunked')
    return ('\r\n'.join(lines) + '\r\n\r\n').encode('ascii')


async def forward_response(request, reader, sink, response=None, cache_file=None):
    response = response or parse_response(await read_head(reader))
    status, _, length, chunked = response
    has_body = request.method == 'GET' and status not in (204, 205, 304)
    output_chunks = has_body and length is None
    await sink(response_head(response, chunked=output_chunks))
    if has_body:
        async with asyncio.timeout(300):
            async for data in body_chunks(reader, length, chunked):
                if cache_file is not None:
                    cache_file.write(data)
                await sink(f'{len(data):x}\r\n'.encode() + data + b'\r\n' if output_chunks else data)
            if output_chunks:
                await sink(b'0\r\n\r\n')


def cache_key(request, destination):
    artifact = destination.upstream.get('artifact') or destination.suffix.endswith(('.rpm', '.jar', '.tgz', '.zip', '.whl'))
    if (request.method != 'GET' or not artifact
            or any(key != 'accept' for key in request.headers)):
        return None
    return destination.profile, destination.revision, destination.url, request.headers.get('accept', '')


def cacheable(response):
    status, headers, length, _ = response
    directives = {part.strip().split('=', 1)[0].lower() for part in headers.get('cache-control', '').split(',')}
    return (status == 200 and length is not None and not headers.get('vary')
            and not directives & {'no-store', 'private', 'no-cache', 'max-age', 's-maxage'})


def redirect_route(destination, location):
    if not location or not location.isascii() or any(char in location for char in '\\?#'):
        raise Rejected('upstream-redirect-denied')
    try:
        target = urlsplit(urljoin(destination.url, location))
    except ValueError:
        raise Rejected('upstream-redirect-denied') from None
    base = urlsplit(destination.upstream['base_url'])
    if (target.scheme, target.netloc) != (base.scheme, base.netloc) or not target.path.startswith(base.path):
        raise Rejected('upstream-redirect-denied')
    ecosystem = destination.upstream['ecosystem']
    suffix = route_parts(target.path[len(base.path):], ecosystem)
    if destination.upstream.get('artifact'):
        value = rpm_artifact(suffix, destination.upstream.get('layout')) if ecosystem == 'rpm' else artifact_path(ecosystem, suffix)
    else:
        value = primary_path(destination.upstream, suffix)
    return Route(destination.profile, destination.revision, destination.upstream, value)


def metadata_link(raw, destination):
    url = mirror_metadata.absolute_link(raw, destination.url)
    if url is None:
        return None
    prefix = f'/mirror/{destination.profile}/{destination.upstream["id"]}/'
    ecosystem = destination.upstream['ecosystem']
    if ecosystem == 'npm':
        prefix = 'http://' + LOCAL_AUTHORITY + prefix
    for number, origin in enumerate([destination.upstream, *destination.upstream.get('artifact_bases', ())]):
        base = urlsplit(origin['base_url'])
        if (url.scheme, url.netloc) != (base.scheme, base.netloc) or not url.path.startswith(base.path):
            continue
        path = url.path[len(base.path):]
        try:
            if ecosystem == 'pypi' and number == 0 and mirror_metadata.python_index(path) and not url.fragment:
                return prefix + path, path.rstrip('/').rsplit('/', 1)[-1]
            # PyPI can escape plus signs in filenames. A slash, dot escape
            # or second layer of encoding stays outside the artifact route.
            path = re.sub(r'%2[bB]', '+', path)
            value = artifact_path(ecosystem, route_parts(path, ecosystem))
        except Rejected:
            continue
        if url.fragment and not re.fullmatch(r'[A-Za-z0-9_-]+=[0-9A-Fa-f]+', url.fragment):
            return None
        tail = ('#' + url.fragment) if url.fragment else ''
        return prefix + f'artifacts/{number}/' + value + tail, unquote(value.rsplit('/', 1)[-1])
    return None


async def index_data(reader, response):
    _, _, length, chunked = response
    data = bytearray()
    async with asyncio.timeout(20):
        async for chunk in body_chunks(reader, length, chunked):
            if len(data) + len(chunk) > MAX_INDEX:
                raise Rejected('mirror-index-too-large')
            data.extend(chunk)
    return data


def cargo_download(raw, destination):
    url = mirror_metadata.absolute_link(raw, destination.url)
    if url is None or url.fragment:
        raise Rejected('cargo-download-prefix-denied')
    for number, origin in enumerate([destination.upstream, *destination.upstream.get('artifact_bases', ())]):
        base = urlsplit(origin['base_url'])
        path = url.path.rstrip('/') + '/' if url.path.rstrip('/') == base.path.rstrip('/') else url.path
        if (url.scheme, url.netloc) != (base.scheme, base.netloc) or not path.startswith(base.path):
            continue
        template = path[len(base.path):].rstrip('/')
        sample = re.sub(r'\{(?:crate|version|prefix|lowerprefix|sha256-checksum)\}', 'fixture', template)
        if sample:
            clean_segments('/' + sample)
        prefix = f'http://{LOCAL_AUTHORITY}/mirror/{destination.profile}/{destination.upstream["id"]}/artifacts/{number}'
        return prefix + ('/' + template if template else '')
    raise Rejected('cargo-download-prefix-denied')


class Client:
    def __init__(self, ca_bundle=None, resolver=resolved_addresses):
        self.context = ssl.create_default_context(cafile=ca_bundle)
        self.resolver = resolver
        self.pending = set()

    async def connect(self, destination):
        url = urlsplit(destination.url)
        host, port = url.hostname, url.port or 443
        loop = asyncio.get_running_loop()
        if len(self.pending) >= 16:
            raise Rejected('mirror-dns-budget')
        query = loop.run_in_executor(None, self.resolver, host, port, destination.upstream.get('addresses'))
        self.pending.add(query)

        def released(future):
            self.pending.discard(future)
            if not future.cancelled():
                future.exception()

        query.add_done_callback(released)
        try:
            addresses = await asyncio.wait_for(asyncio.shield(query), 10)
        except PolicyError as error:
            raise Rejected(str(error)) from None
        async with asyncio.timeout(15):
            for family, kind, protocol, address in addresses:
                try:
                    peer = socket.socket(family, kind, protocol)
                except OSError:
                    continue
                peer.setblocking(False)
                try:
                    await asyncio.wait_for(loop.sock_connect(peer, address), 5)
                    return await asyncio.open_connection(sock=peer, limit=HEADER_LIMIT, ssl=self.context,
                                                         server_hostname=host, ssl_handshake_timeout=5,
                                                         ssl_shutdown_timeout=1)
                except ssl.SSLCertVerificationError:
                    peer.close()
                    raise Rejected('upstream-certificate-rejected') from None
                except (OSError, asyncio.TimeoutError):
                    peer.close()
                except BaseException:
                    peer.close()
                    raise
        raise Rejected('mirror-upstream-unavailable')

    @asynccontextmanager
    async def fetch(self, request, destination):
        for attempt in range(4):
            reader, writer = await self.connect(destination)
            try:
                writer.write(upstream_request(request, destination))
                await asyncio.wait_for(writer.drain(), 10)
                response = parse_response(await read_head(reader))
                if response[0] not in REDIRECTS:
                    yield reader, response
                    return
                if attempt == 3:
                    raise Rejected('upstream-redirect-limit')
                destination = redirect_route(destination, response[1].get('location'))
            finally:
                writer.close()

    async def verify(self, profile, upstream):
        try:
            adapter = upstream['ecosystem']
            probe = upstream.get('probe_path')
            if probe is None and adapter == 'go':
                probe = re.sub(r'[A-Z]', lambda match: '!' + match[0].lower(), upstream['module_prefixes'][0]) + '/@v/list'
            suffix = primary_path(upstream, route_parts(probe or INDEX_PATHS[adapter], adapter))
        except KeyError:
            raise Rejected('mirror-index-probe-unavailable') from None
        destination = Route(profile['name'], revision(profile), upstream, suffix)
        async with self.fetch(Request('GET', '', {}), destination) as (reader, response):
            status, headers, _, _ = response
            if status != 200:
                raise Rejected(f'mirror-index-http-{status}')
            data = await index_data(reader, response)
            if adapter in ('pypi', 'npm', 'cargo'):
                rewrite_index(data, headers, destination)
                return
            if adapter == 'go':
                try:
                    if all(GO_VERSION.fullmatch(line) for line in data.decode('ascii').splitlines()):
                        return
                except UnicodeDecodeError:
                    pass
                raise Rejected('invalid-go-version-index')
            if b'<!DOCTYPE' in data:
                raise Rejected('invalid-repository-index')
            try:
                index = ElementTree.fromstring(data)
            except ElementTree.ParseError:
                raise Rejected('invalid-repository-index') from None
            roots = {'rpm': '{http://linux.duke.edu/metadata/repo}repomd', 'maven': 'metadata'}
            if index.tag != roots[adapter]:
                raise Rejected('invalid-repository-index')

    async def transfer(self, request, destination, sink, cache=None):
        ecosystem = destination.upstream['ecosystem']
        metadata = (not destination.upstream.get('artifact') and (ecosystem == 'pypi' or
                    (ecosystem == 'npm' and not destination.suffix.endswith('.tgz')) or
                    (ecosystem == 'cargo' and destination.suffix == 'config.json')))
        if metadata and 'range' in request.headers:
            raise Rejected('mirror-index-range-denied')
        key = cache_key(request, destination) if cache is not None else None
        if key is not None:
            with cache.read(key) as hit:
                if hit is not None:
                    response, handle = hit
                    await sink(response_head(response))
                    while data := handle.read(CHUNK):
                        await sink(data)
                    return
        async with self.fetch(request, destination) as (reader, response):
            if metadata and response[0] == 200:
                headers = {key: value for key, value in response[1].items()
                           if key in ('content-type', 'cache-control', 'last-modified')}
                if request.method == 'HEAD':
                    await sink(response_head((200, headers, None, False)))
                    return
                data = rewrite_index(await index_data(reader, response), response[1], destination)
                if len(data) > MAX_INDEX:
                    raise Rejected('mirror-index-too-large')
                await sink(response_head((200, headers, len(data), False)))
                await sink(data)
            elif key is None or not cacheable(response):
                await forward_response(request, reader, sink, response)
            else:
                with cache.write(key, response) as handle:
                    await forward_response(request, reader, sink, response, handle)


def rewrite_index(data, headers, destination):
    if headers.get('content-encoding', 'identity').lower() != 'identity':
        raise Rejected('unsupported-mirror-index-encoding')
    try:
        def link(raw):
            return metadata_link(raw, destination)

        ecosystem = destination.upstream['ecosystem']
        if ecosystem == 'pypi':
            return mirror_metadata.pypi(data, headers.get('content-type', 'text/html'), link)
        if ecosystem == 'npm':
            return mirror_metadata.npm(data, link)
        value = json.loads(data)
        if not isinstance(value, dict) or value.get('auth-required') is True:
            raise Rejected('invalid-cargo-config')
        return json.dumps({'dl': cargo_download(value.get('dl'), destination)}, separators=(',', ':')).encode()
    except (ValueError, RecursionError):
        raise Rejected('invalid-mirror-index') from None
