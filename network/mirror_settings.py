"""Settings for the first approved upstream of each package manager."""

from pathlib import Path
from xml.etree import ElementTree

BASE = 'http://127.0.0.1:18081/mirror/'
GUEST = '/opt/sandbox-egress/client'


def select_urls(profiles):
    urls = {}
    for name, profile in profiles.items():
        for upstream in profile['upstreams']:
            urls.setdefault(upstream['ecosystem'], BASE + name + '/' + upstream['id'] + '/')
    return urls


def maven_settings(directory, url):
    settings = ElementTree.Element('settings')
    mirrors = ElementTree.SubElement(settings, 'mirrors')
    mirror = ElementTree.SubElement(mirrors, 'mirror')
    for name, value in (('id', 'sandbox-dependency-mirror'), ('mirrorOf', '*'), ('url', url)):
        ElementTree.SubElement(mirror, name).text = value
    ElementTree.ElementTree(settings).write(directory / 'maven-settings.xml', encoding='utf-8', xml_declaration=True)


def settings(directory, profiles):
    directory = Path(directory)
    urls = select_urls(profiles)
    env = {}
    if 'maven' in urls:
        directory.mkdir(mode=0o700, exist_ok=True)
        maven_settings(directory, urls['maven'])
        env['MAVEN_ARGS'] = '--settings ' + GUEST + '/maven-settings.xml'
    if 'pypi' in urls:
        env['PIP_INDEX_URL'] = urls['pypi'] + 'simple/'
        env['PIP_EXTRA_INDEX_URL'] = ''
    if 'npm' in urls:
        env.update(npm_config_registry=urls['npm'], npm_config_audit='false')
    if 'cargo' in urls:
        directory.mkdir(mode=0o700, exist_ok=True)
        (directory / 'cargo.toml').write_text('[source.crates-io]\nreplace-with = "sandbox-mirror"\n'
                                             '[source.sandbox-mirror]\nregistry = "sparse+' + urls['cargo'] + '"\n')
    if 'go' in urls:
        env.update(GOPROXY=urls['go'], GONOPROXY='none', GONOSUMDB='none', GOSUMDB='sum.golang.org')
    return env
