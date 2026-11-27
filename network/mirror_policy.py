"""Validate the profile data shared by the installed launcher and trusted mirror."""

import ipaddress
import json
import re
from urllib.parse import urlsplit, urlunsplit

from policy import PolicyError, fields, hostname, unique_object

NAME = re.compile(r'[a-z0-9][a-z0-9._-]{0,63}')
REVISION = re.compile(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,63}')
SEGMENT = re.compile(r'[A-Za-z0-9._+~-]+')
ECOSYSTEMS = frozenset(('rpm', 'maven', 'pypi', 'npm', 'cargo', 'go'))
MAX_PROFILE = 65536
MAX_SELECTION = 8192
MAX_NAMES = 64


def is_name(value):
    return isinstance(value, str) and NAME.fullmatch(value) is not None


def decode(data, limit=MAX_PROFILE):
    if len(data) > limit:
        raise PolicyError('mirror input exceeds its size limit')
    try:
        return json.loads(data.decode('utf-8'), object_pairs_hook=unique_object)
    except (UnicodeError, ValueError, RecursionError):
        raise PolicyError('invalid mirror JSON or duplicate keys') from None


def names(value):
    if not isinstance(value, list) or len(value) > MAX_NAMES or not all(map(is_name, value)):
        raise PolicyError('mirror profile names must be a bounded array of valid names')
    return list(dict.fromkeys(value))


def base_url(value):
    if not isinstance(value, str) or not value.isascii() or len(value) > 2048 or any(
            ord(char) <= 32 or ord(char) >= 127 or char in '\\?#' for char in value):
        raise PolicyError('invalid mirror base URL')
    try:
        url = urlsplit(value)
        port = url.port or 443
    except ValueError:
        raise PolicyError('invalid mirror base URL authority') from None
    if url.scheme != 'https' or not url.hostname or url.username is not None or url.port == 0:
        raise PolicyError('mirror upstream requires HTTPS and a credential-free authority')
    host = hostname(url.hostname)
    # A canonical directory prefix lets route checks compare path components.
    segments = url.path.removeprefix('/').removesuffix('/').split('/') if url.path not in ('', '/') else []
    if any(segment in ('.', '..') or not SEGMENT.fullmatch(segment) for segment in segments):
        raise PolicyError('invalid mirror base URL path')
    return urlunsplit(('https', host if port == 443 else f'{host}:{port}',
                       '/' + ''.join(segment + '/' for segment in segments), '', ''))


def lan_addresses(values):
    if not isinstance(values, list) or not 1 <= len(values) <= 8:
        raise PolicyError('mirror LAN upstream requires a bounded address list')
    try:
        addresses = [ipaddress.ip_address(value) for value in values
                     if isinstance(value, str) and '%' not in value]
    except ValueError:
        raise PolicyError('invalid mirror LAN address') from None
    if len(set(addresses)) != len(values) or any(
        address.is_loopback or address.is_link_local or address.is_multicast
        or address.is_unspecified or address.is_reserved
        or getattr(address, 'ipv4_mapped', None) is not None
        for address in addresses
    ):
        raise PolicyError('unsafe or duplicate mirror LAN addresses')
    return [str(address) for address in addresses]


def module_prefixes(value):
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_NAMES:
        raise PolicyError('Go mirror upstream requires a bounded list of module prefixes')
    for prefix in value:
        if not isinstance(prefix, str) or len(prefix) > 512:
            raise PolicyError('invalid Go module prefix')
        host, *parts = prefix.split('/')
        if hostname(host) != host or any(part in ('.', '..') or not SEGMENT.fullmatch(part) for part in parts):
            raise PolicyError('invalid Go module prefix')
    return list(dict.fromkeys(value))


def prefix_config(value, *, catalog):
    result = {'base_url': base_url(value['base_url'])}
    if 'addresses' in value:
        if catalog:
            raise PolicyError('public catalog profiles cannot declare LAN exceptions')
        result['addresses'] = lan_addresses(value['addresses'])
    return result


def upstream(value, *, catalog=False):
    fields(value, ('id', 'ecosystem', 'base_url'), ('addresses', 'module_prefixes', 'artifact_bases', 'layout', 'probe_path'))
    ecosystem = value['ecosystem']
    if not is_name(value['id']) or not isinstance(ecosystem, str) or ecosystem not in ECOSYSTEMS:
        raise PolicyError('invalid mirror upstream ID or unsupported ecosystem')
    result = {'id': value['id'], 'ecosystem': ecosystem, **prefix_config(value, catalog=catalog)}
    if 'probe_path' in value:
        probe = value['probe_path']
        if not isinstance(probe, str) or not probe or len(probe) > 4096 or probe.startswith('/'):
            raise PolicyError('invalid mirror index probe path')
        result['probe_path'] = probe
    if 'artifact_bases' in value:
        records = value['artifact_bases']
        if not isinstance(records, list) or not 1 <= len(records) <= 8:
            raise PolicyError('artifact bases must be a bounded list of approved prefixes')
        for entry in records:
            fields(entry, ('base_url',), ('addresses',))
        artifacts = [prefix_config(entry, catalog=catalog) for entry in records]
        urls = [item['base_url'] for item in artifacts]
        if len(set(urls)) != len(urls) or result['base_url'] in urls:
            raise PolicyError('duplicate artifact prefix')
        if ecosystem == 'rpm':
            paths = [urlsplit(url).path for url in (result['base_url'], *urls)]
            if any(left.startswith(right) or right.startswith(left)
                   for index, left in enumerate(paths) for right in paths[index + 1:]):
                raise PolicyError('ambiguous split RPM prefix paths')
        result['artifact_bases'] = artifacts
    if 'layout' in value:
        if (ecosystem != 'rpm' or value['layout'] != 'al2023-cdn'
                or not re.fullmatch(r'https://cdn\.amazonlinux\.com/al2023/core/guids/[0-9a-f]{64}/(?:x86_64|aarch64)/',
                                    result['base_url'])
                or result.get('artifact_bases') != [{'base_url': 'https://cdn.amazonlinux.com/al2023/blobstore/'}]
                or 'addresses' in result):
            raise PolicyError('invalid split Amazon Linux 2023 repository layout')
        result['layout'] = 'al2023-cdn'
    if 'module_prefixes' in value or ecosystem == 'go':
        if ecosystem != 'go':
            raise PolicyError('module prefixes require a Go upstream')
        result['module_prefixes'] = module_prefixes(value.get('module_prefixes'))
    return result


def profile(value, *, catalog=False):
    fields(value, ('schema', 'name', 'revision', 'default', 'upstreams'))
    if type(value['schema']) is not int or value['schema'] != 1:
        raise PolicyError('unsupported mirror profile schema')
    revision = value['revision']
    if not is_name(value['name']) or not isinstance(revision, str) or not REVISION.fullmatch(revision):
        raise PolicyError('invalid mirror profile name or revision')
    if type(value['default']) is not bool or not isinstance(value['upstreams'], list) or not (
            1 <= len(value['upstreams']) <= MAX_NAMES):
        raise PolicyError('invalid default flag or upstream list')
    upstreams = [upstream(item, catalog=catalog) for item in value['upstreams']]
    if len({item['id'] for item in upstreams}) != len(upstreams):
        raise PolicyError('duplicate mirror upstream ID')
    return {**value, 'upstreams': upstreams}


def snapshot(value):
    fields(value, ('schema', 'profiles'))
    values = value['profiles']
    if type(value['schema']) is not int or value['schema'] != 1 or not isinstance(values, dict) or len(values) > MAX_NAMES:
        raise PolicyError('invalid mirror snapshot')
    result = {name: profile(data) for name, data in values.items()}
    if any(name != data['name'] for name, data in result.items()):
        raise PolicyError('mirror snapshot profile name mismatch')
    return {'schema': 1, 'profiles': result}
