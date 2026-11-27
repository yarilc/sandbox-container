"""Rewrite the package download references in approved registry metadata."""

import html
from html.parser import HTMLParser
import json
import re
from urllib.parse import urljoin, urlsplit

PYTHON_FILE = re.compile(r'.+\.(?:whl|tar\.gz|tar\.bz2|tar\.xz|zip)(?:\.metadata)?')
PROJECT = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
PYPI_ATTRIBUTES = ('data-requires-python', 'data-yanked', 'data-core-metadata', 'data-dist-info-metadata')


def python_index(path):
    return path == 'simple/' or (path.startswith('simple/') and path.endswith('/')
                                 and PROJECT.fullmatch(path[7:-1]) is not None)


def absolute_link(raw, destination):
    if not isinstance(raw, str) or len(raw) > 4096 or any(ord(c) <= 32 or c == '\\' for c in raw):
        return None
    try:
        url = urlsplit(urljoin(destination, raw))
    except ValueError:
        return None
    return url if url.scheme == 'https' and url.hostname and url.username is None and not url.query else None


class SimplePage(HTMLParser):
    def __init__(self, link):
        super().__init__(convert_charrefs=True)
        self.link = link
        self.links = []

    def handle_starttag(self, tag, attributes):
        values = dict(attributes)
        raw = values.get('href')
        if tag != 'a' or raw is None:
            return
        result = self.link(raw)
        if result is None:
            return
        href, title = result
        rendered = [f'href="{html.escape(href, quote=True)}"']
        for name in PYPI_ATTRIBUTES:
            if name in values:
                rendered.append(f'{name}="{html.escape(values[name] or "", quote=True)}"')
        self.links.append('<a ' + ' '.join(rendered) + '>' + html.escape(title) + '</a>')


def pypi(data, content_type, link):
    if 'json' in content_type:
        value = json.loads(data)
        if not isinstance(value, dict):
            raise ValueError('invalid PyPI JSON')
        for key in ('files', 'projects'):
            if key not in value:
                continue
            items = value[key]
            if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
                raise ValueError('invalid PyPI JSON')
            if key == 'projects':
                continue
            rewritten = []
            for item in items:
                mapped = link(item.get('url'))
                if mapped:
                    rewritten.append(item | {'url': mapped[0]})
            value[key] = rewritten
        return json.dumps(value, separators=(',', ':'), allow_nan=False).encode()
    page = SimplePage(link)
    page.feed(data.decode('utf-8'))
    page.close()
    return ('<!doctype html><html><body>\n' + '\n'.join(page.links) + '\n</body></html>\n').encode()


def npm(data, link):
    value = json.loads(data)
    versions = value.get('versions') if isinstance(value, dict) else None
    if not isinstance(versions, dict):
        raise ValueError('invalid npm registry metadata')
    approved = {}
    for version, item in versions.items():
        dist = item.get('dist') if isinstance(item, dict) else None
        if not isinstance(dist, dict):
            continue
        mapped = link(dist.get('tarball'))
        if mapped:
            approved[version] = item | {'dist': dist | {'tarball': mapped[0]}}
    value['versions'] = approved
    return json.dumps(value, separators=(',', ':'), allow_nan=False).encode()
