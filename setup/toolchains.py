"""Operator-managed toolchain library shared by the wrappers (standard library only).

Toolchains are relocatable prefixes extracted from one or more digest-pinned
image paths or checksummed archives. Sessions see the library read-only at
/toolchains.
"""
import contextlib
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import ssl
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
from urllib.parse import urlsplit
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PROFILE, WINDOWS_ENTRY, SetupError, absolute, overlap, private  # noqa: E402
import agent_profile  # noqa: E402  (on the path through common)

INSTALLATION = Path(__file__).resolve().parents[1]
# Reviewed recipes installed with the release; `add <name>` reads them.
CATALOG = INSTALLATION / 'setup/toolchain-catalog'
LIBRARY_NAME = 'sandbox-toolchains'
MOUNT = '/toolchains'
# The index schema stays 1: wrappers on older reference tags read the shared
# library. Only the recipe format, an input, gains schema 2 (several sources).
SCHEMA = 1
RECIPE_SCHEMAS = (1, 2)
RECIPE_SCHEMA = 2
MAX_SOURCES = 16
NAME = re.compile(r'[a-z0-9][a-z0-9._-]{0,63}')
VERSION = re.compile(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,63}')
ENV_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,63}')
RELATIVE = re.compile(r'(?:[A-Za-z0-9._+-]+(?:/[A-Za-z0-9._+-]+)*)?')
IMAGE = re.compile(r'[a-z0-9][a-z0-9._/:-]*@sha256:[a-f0-9]{64}')
SHA256 = re.compile(r'[a-f0-9]{64}')
FROM = re.compile(r'^\s*FROM\s+(\S+)', re.IGNORECASE | re.MULTILINE)
BASE = re.compile(r'\S+@sha256:[a-f0-9]{64}')
RECIPE_REQUIRED = {'schema', 'name', 'version', 'check', 'default'}
RECIPE_OPTIONAL = {'path', 'env', 'requires', 'notes'}
# Required and optional keys of each source kind in schema 2; schema 1 has no
# URL source, no member path and no target.
SOURCE_KEYS = {'image': ({'image', 'path'}, {'target'}),
               'url': ({'url', 'sha256'}, {'path', 'strip_components', 'target'}),
               'archive': ({'archive', 'sha256'}, {'path', 'strip_components', 'target'})}
# Session variables that a toolchain must never replace, in two groups. The
# neutral group is the same for every wrapper and is defined with the profile
# loader (agent_profile.NEUTRAL_ENV).
PROTECTED = {name.lower() for name in agent_profile.NEUTRAL_ENV}
PROTECTED_PREFIXES = tuple(prefix.lower() for prefix in agent_profile.NEUTRAL_ENV_PREFIXES)
# The profile group belongs to the wrapper running this module. The library is
# shared, so another wrapper may have installed a toolchain that sets one of
# these: launch-env then leaves it out of this wrapper's sessions with a warning.
# The group covers the prefix, configuration, approval and credential variables
# and the agent's own variables and prefixes (native.protected_env).


def profile_protection(profile):
    """Return the lowercase protected names and prefixes of one profile."""
    agent = profile.protected_env
    names = {name.lower() for name in (profile.config_dir_env, profile.approval_bypass_env,
                                       *profile.credential_envs, *(e for e in agent if not e.endswith('_')))
             if name}
    prefixes = (profile.env_prefix.lower() + '_', *(e.lower() for e in agent if e.endswith('_')))
    return names, prefixes


PROFILE_PROTECTED, PROFILE_PREFIXES = profile_protection(PROFILE)
CHECK_TIMEOUT = 300
PREFIX = PROFILE.message_prefix
# Archive downloads: largest accepted archive, and the timeout of the
# connection and of each read, in seconds.
DOWNLOAD_LIMIT = 4 << 30
DOWNLOAD_TIMEOUT = 60
# The launcher's default host CA bundles, in order (launcher/core.sh).
CA_CANDIDATES = ('/etc/ssl/certs/ca-certificates.crt', '/etc/pki/tls/certs/ca-bundle.crt')


def run(args, timeout=None):
    """Run one engine command and capture its text output."""
    try:
        return subprocess.run(['podman', *args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SetupError('podman ' + ' '.join(args[:2]) + ' failed: ' + str(error)) from None


@contextlib.contextmanager
def stream(args):
    """Yield the binary standard output of one engine command."""
    try:
        process = subprocess.Popen(['podman', *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as error:
        raise SetupError('podman ' + args[0] + ' failed: ' + str(error)) from None
    try:
        yield process.stdout
        process.stdout.read()
    finally:
        process.stdout.close()
        error = process.stderr.read().decode(errors='replace')
        process.stderr.close()
        if process.wait() != 0:
            raise SetupError('podman ' + args[0] + ' failed: ' + error.strip()[-400:])


# Library location and safety

def library_path(env):
    value = env.get(PROFILE.env('TOOLCHAINS_DIR'), '')
    if value:
        if '\t' in value or not value.startswith('/'):
            raise SetupError(PROFILE.env('TOOLCHAINS_DIR') + ' must be an absolute path without tabs.')
        return Path(absolute(value))
    data = env.get('XDG_DATA_HOME', '')
    if not data.startswith('/'):
        data = str(Path(env['HOME']) / '.local/share')
    return Path(absolute(data)) / LIBRARY_NAME


def prepare_library(path, avoid):
    path = Path(path)
    if any(c in str(path) for c in '\t\r\n\0:'):
        raise SetupError(f'Toolchain library path must not contain tabs, colons or control characters: {path}')
    for other in avoid:
        if overlap(path, other):
            raise SetupError(f'Toolchain library {path} overlaps {other}; it must stay outside the workspace, '
                             'state directories and installation.')
    try:
        return private(path, create=True)
    except SetupError as error:
        raise SetupError(f'Toolchain library {path}: {error}') from None


def state_directories(env):
    """Host state directories the toolchain command can derive without a session."""
    state = env.get(PROFILE.env('STATE_DIR'), '')
    if state:
        return [Path(state)]
    home = Path(env['HOME'])
    config = env.get(PROFILE.config_dir_env, '') or str(home / PROFILE.config_home)
    return [Path(config), *(home / shared for shared in PROFILE.shared_dirs)]


@contextlib.contextmanager
def locked(library):
    descriptor = os.open(library / '.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def write_atomic(path, text):
    descriptor, temporary = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as handle:
            handle.write(text)
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)
        raise


def base_reference(installation):
    """The single digest-pinned base named by the installed runtime recipe."""
    try:
        text = (Path(installation) / 'Containerfile').read_text()
    except OSError as error:
        raise SetupError('Cannot read the runtime Containerfile: ' + str(error)) from None
    bases = FROM.findall(text)
    if len(bases) != 1 or not BASE.fullmatch(bases[0]):
        raise SetupError('The runtime Containerfile must have exactly one digest-pinned FROM line.')
    return bases[0]


# Recipes

def control_free(value):
    return isinstance(value, str) and not any(ord(c) < 0x20 or ord(c) == 0x7f for c in value)


def relative(value, where):
    if not isinstance(value, str) or not RELATIVE.fullmatch(value) or \
            any(part in ('.', '..') for part in value.split('/')):
        raise SetupError(f'toolchain recipe: {where} must be a relative path inside the toolchain')
    return value


def neutral_protected(variable):
    lowered = variable.lower()
    return lowered in PROTECTED or lowered.startswith(PROTECTED_PREFIXES)


def profile_protected(variable):
    lowered = variable.lower()
    return lowered in PROFILE_PROTECTED or lowered.startswith(PROFILE_PREFIXES)


def protected(variable):
    return neutral_protected(variable) or profile_protected(variable)


def https_url(value, limit=2048):
    """An https URL without credentials, whitespace or control characters."""
    if not isinstance(value, str) or len(value) > limit or not control_free(value) or \
            any(c.isspace() for c in value):
        return False
    try:
        parts = urlsplit(value)
    except ValueError:
        return False
    return parts.scheme == 'https' and bool(parts.hostname) and '@' not in parts.netloc


def validate_source(source, schema, where):
    """One normalized source; the target is '' for the toolchain root."""
    def fail(text):
        raise SetupError('toolchain recipe: ' + where + ': ' + text)
    if not isinstance(source, dict):
        fail('must be an object')
    kinds = [kind for kind in SOURCE_KEYS if kind in source]
    if len(kinds) != 1 or (schema == 1 and kinds[0] == 'url'):
        fail('needs image and path, ' + ('url and sha256, ' if schema > 1 else '') + 'or archive and sha256')
    kind = kinds[0]
    required, optional = SOURCE_KEYS[kind]
    if schema == 1:
        optional = optional & {'strip_components'}
    if not required <= set(source) or not set(source) <= required | optional:
        fail('an ' + kind + ' source has ' + ', '.join(sorted(required)) +
             (' and optional ' + ', '.join(sorted(optional)) if optional else '') + ' (unknown keys rejected)')
    if kind == 'image':
        if not isinstance(source['image'], str) or not IMAGE.fullmatch(source['image']):
            fail('the image must be referenced by @sha256: digest')
        path = source['path']
        if not isinstance(path, str) or not path.startswith('/') or path == '/' or not control_free(path) or \
                any(part in ('.', '..') for part in path.split('/')):
            fail('the image path must be an absolute path below /')
    else:
        if kind == 'url' and not https_url(source['url']):
            fail('the URL must be an https:// URL without credentials or spaces')
        if kind == 'archive':
            if not isinstance(source['archive'], str) or not source['archive'].startswith('/'):
                fail('the archive must be an absolute local file path')
            absolute(source['archive'])
        if not isinstance(source['sha256'], str) or not SHA256.fullmatch(source['sha256']):
            fail('the archive SHA-256 must be 64 lowercase hex digits')
        if 'path' in source and 'strip_components' in source:
            fail('use either path or strip_components')
        strip = source.get('strip_components', 0)
        if not isinstance(strip, int) or isinstance(strip, bool) or not 0 <= strip <= 8:
            fail('strip_components must be an integer from 0 to 8')
        if 'path' in source and (not relative(source['path'], where + ' path') or len(source['path']) > 512):
            fail('path must name a directory inside the archive')
    target = source.get('target', '')
    relative(target, where + ' target')
    return {**source, 'target': target}


def validate_recipe(value):
    if not isinstance(value, dict):
        raise SetupError('toolchain recipe must be a JSON object')
    if 'schema' not in value:
        raise SetupError('toolchain recipe: missing key schema')
    schema = value['schema']
    if type(schema) is not int or schema not in RECIPE_SCHEMAS:
        raise SetupError('toolchain recipe: schema must be 1 or 2')
    source_key = 'source' if schema == 1 else 'sources'
    required = RECIPE_REQUIRED | {source_key}
    unknown = set(value) - required - RECIPE_OPTIONAL
    if unknown:
        raise SetupError('toolchain recipe: unknown key ' + ', '.join(sorted(unknown)))
    missing = required - set(value)
    if missing:
        raise SetupError('toolchain recipe: missing key ' + ', '.join(sorted(missing)))
    if not isinstance(value['name'], str) or not NAME.fullmatch(value['name']):
        raise SetupError('toolchain recipe: invalid toolchain name; use [a-z0-9][a-z0-9._-]{0,63}')
    if not isinstance(value['version'], str) or not VERSION.fullmatch(value['version']):
        raise SetupError('toolchain recipe: invalid version')
    if schema == 1:
        sources = [validate_source(value['source'], 1, 'source')]
    else:
        listed = value['sources']
        if not isinstance(listed, list) or not 0 < len(listed) <= MAX_SOURCES:
            raise SetupError(f'toolchain recipe: sources must be a list of 1 to {MAX_SOURCES} sources')
        sources = [validate_source(item, 2, f'sources[{index}]') for index, item in enumerate(listed)]
    paths = value.get('path', ['bin'])
    if not isinstance(paths, list) or len(paths) > 8:
        raise SetupError('toolchain recipe: path must be a list of at most 8 relative paths')
    for entry in paths:
        relative(entry, 'path entry')
    environment = value.get('env', {})
    if not isinstance(environment, dict) or len(environment) > 32:
        raise SetupError('toolchain recipe: env must be an object with at most 32 variables')
    for variable, item in environment.items():
        if not ENV_NAME.fullmatch(variable):
            raise SetupError('toolchain recipe: invalid env variable name ' + repr(variable))
        if protected(variable):
            raise SetupError('toolchain recipe: env variable ' + variable + ' is protected by the session')
        if not isinstance(item, dict) or len(item) != 1 or not set(item) <= {'toolchain', 'value'}:
            raise SetupError('toolchain recipe: env value for ' + variable + ' must be {"toolchain": path} or {"value": text}')
        if 'toolchain' in item:
            relative(item['toolchain'], 'env ' + variable)
        elif not control_free(item['value']) or len(item['value']) > 1024:
            raise SetupError('toolchain recipe: env literal for ' + variable + ' must be text without control characters')
    requires = value.get('requires', [])
    if not isinstance(requires, list) or len(requires) > 16 or len(set(requires)) != len(requires) or \
            not all(isinstance(item, str) and NAME.fullmatch(item) for item in requires) or value['name'] in requires:
        raise SetupError('toolchain recipe: requires must list other toolchain names once each')
    notes = value.get('notes', [])
    if not isinstance(notes, list) or len(notes) > 10 or \
            not all(control_free(item) and 0 < len(item) <= 300 for item in notes):
        raise SetupError('toolchain recipe: notes must be at most 10 single-line texts')
    check = value['check']
    if not isinstance(check, list) or not 0 < len(check) <= 32 or \
            not all(control_free(item) and item for item in check):
        raise SetupError('toolchain recipe: check must be a non-empty command list without control characters')
    if not isinstance(value['default'], bool):
        raise SetupError('toolchain recipe: default must be true or false')
    return {'schema': RECIPE_SCHEMA, 'name': value['name'], 'version': value['version'], 'sources': sources,
            'path': list(paths), 'env': {k: dict(v) for k, v in environment.items()}, 'requires': list(requires),
            'notes': list(notes), 'check': list(check), 'default': value['default']}


def load_recipe(path, translate=None):
    """Read and validate a recipe; translate maps local archive paths first (Windows entry)."""
    try:
        value = json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        raise SetupError('Cannot read toolchain recipe ' + str(path) + ': ' + str(error)) from None
    if translate and isinstance(value, dict):
        listed = [value.get('source')] if value.get('schema') == 1 else value.get('sources')
        for source in listed if isinstance(listed, list) else ():
            if isinstance(source, dict) and isinstance(source.get('archive'), str):
                source['archive'] = translate(source['archive'])
    return validate_recipe(value)


def catalog(directory=None):
    """The release's reviewed recipes by name: pinned images and HTTPS archives only."""
    directory = Path(directory or CATALOG)
    found = {}
    if not directory.is_dir():
        return found
    for path in sorted(directory.glob('*.json')):
        recipe = load_recipe(path)
        if recipe['name'] != path.stem:
            raise SetupError('Catalog recipe ' + path.name + ' names the toolchain ' + recipe['name'])
        if any('archive' in source for source in recipe['sources']):
            raise SetupError('Catalog recipe ' + path.name + ' names a local archive; use an HTTPS URL')
        found[recipe['name']] = recipe
    return found


def catalog_name(argument):
    """A catalog name has no slash and no .json suffix; anything else is a recipe file."""
    return '/' not in argument and not argument.endswith('.json')


def saved_worktree_scope():
    """Whether setup saved the parent-directory scope for this release; a checkout saves nothing."""
    try:
        value = json.loads((INSTALLATION / 'setup.json').read_text())
    except FileNotFoundError:
        return False
    except (OSError, ValueError):
        raise SetupError('Cannot read the saved preferences in ' + str(INSTALLATION) + '; rerun --container-setup.')
    return isinstance(value, dict) and value.get('worktree') is True


def check_recipe_location(path, env):
    """Refuse a recipe that a session started from here could have written (design D6)."""
    recipe = Path(path).resolve()
    workspace = Path.cwd().resolve()
    if saved_worktree_scope():
        workspace = workspace.parent
    for mount in (workspace, *(Path(state).resolve() for state in state_directories(env))):
        if recipe == mount or mount in recipe.parents:
            raise SetupError('Toolchain recipe ' + str(recipe) + ' is inside ' + str(mount) + ', which a session '
                             'started from here can write; keep operator recipes outside project and state '
                             'directories, or add a catalog recipe by name.')


# Windows paths that reach the toolchain command unchanged through the Windows
# entry; the rules follow launcher/windows/bootstrap.sh.
WINDOWS_DRIVE = re.compile(r'[A-Za-z]:[\\/]')
WSL_PREFIXES = ('\\\\wsl$\\', '\\\\wsl.localhost\\', '//wsl$/', '//wsl.localhost/')


# The drive mounts are read from this mount namespace, the one where the files
# are opened: the command runs inside the machine's systemd namespaces.
MOUNTINFO = Path('/proc/self/mountinfo')
DRIVE_ROOT = re.compile(r'(?:^|[,;])path=([A-Za-z]):\\(?:[;,]|$)')
MOUNT_ESCAPE = re.compile(r'\\([0-7]{3})')


def drive_mounts():
    """Mount points of whole Windows drives (drvfs path=X:\\), by lowercase drive letter."""
    mounts = {}
    try:
        lines = MOUNTINFO.read_text().splitlines()
    except OSError:
        return mounts
    for line in lines:
        fields, _, filesystem = line.partition(' - ')
        fields, filesystem = fields.split(), filesystem.split()
        # Only the drive root: bind mounts of a subdirectory have another root.
        if len(fields) < 5 or len(filesystem) < 3 or fields[3] != '/':
            continue
        match = DRIVE_ROOT.search(filesystem[2])
        if match:
            # mountinfo writes spaces and other special characters as octal escapes.
            point = MOUNT_ESCAPE.sub(lambda octal: chr(int(octal.group(1), 8)), fields[4])
            mounts.setdefault(match.group(1).lower(), point)
    return mounts


def windows_path(value):
    """Translate a Windows drive path given through the Windows entry; other paths are unchanged."""
    lowered = value.lower()
    if lowered.startswith(WSL_PREFIXES):
        raise SetupError(value + ' is inside a WSL distribution; use a file on a Windows drive such as C:')
    if lowered.startswith(('\\\\', '//')):
        raise SetupError(value + ' is a network or device path; use a file on a local Windows drive')
    if not WINDOWS_DRIVE.match(value):
        return value
    mount = drive_mounts().get(value[0].lower())
    if not mount:
        raise SetupError(value + ' is on drive ' + value[:2].upper() + ', which this distribution does not mount')
    translated = mount.rstrip('/') + '/' + value[3:].replace('\\', '/')
    if not Path(translated).exists():
        raise SetupError(value + ' does not exist (' + translated + ' in the distribution)')
    return translated


def resolve_recipe(argument, env):
    argument = str(argument)
    translate = windows_path if env.get(WINDOWS_ENTRY) else None
    if translate and (WINDOWS_DRIVE.match(argument) or argument.startswith(('\\\\', '//'))):
        argument = translate(argument)
    if not catalog_name(argument):
        check_recipe_location(argument, env)
        return load_recipe(argument, translate)
    recipes = catalog()
    if argument not in recipes:
        raise SetupError('No catalog recipe named ' + argument + '; available: ' + (', '.join(recipes) or 'none') +
                         '. Give a path ending in .json for a recipe file.')
    return recipes[argument]


# Installed toolchains

def installed(library):
    found = {}
    for entry in sorted(Path(library).iterdir()):
        manifest = entry / 'toolchain.json'
        if entry.name.startswith('.') or not entry.is_dir() or entry.is_symlink() or not manifest.is_file():
            continue
        try:
            value = json.loads(manifest.read_text())
        except ValueError:
            raise SetupError('Invalid toolchain manifest: ' + entry.name + '; remove and add it again.') from None
        if value.get('name') != entry.name:
            raise SetupError('Toolchain manifest name mismatch: ' + entry.name)
        found[entry.name] = value
    return found


def container_value(name, item):
    if 'toolchain' in item:
        return MOUNT + '/' + name + ('/' + item['toolchain'] if item['toolchain'] else '')
    return item['value']


def container_paths(name, value):
    return [MOUNT + '/' + name + ('/' + entry if entry else '') for entry in value['path']]


def commands(root, paths):
    found = set()
    for entry in paths:
        directory = root / entry if entry else root
        if not directory.is_dir() or directory.is_symlink():
            continue
        for item in directory.iterdir():
            target = item.resolve()
            if (target == root or root in target.parents) and target.is_file() and os.access(target, os.X_OK):
                found.add(item.name)
    return sorted(found)


def quoted(value):
    """Always single-quote, so env.sh never expands or runs anything."""
    return "'" + value.replace("'", "'\"'\"'") + "'"


def env_script(name, value):
    lines = ['# Generated by the toolchain library; do not edit.']
    for required in value['requires']:
        lines.append('. ' + MOUNT + '/' + required + '/env.sh')
    for variable, item in sorted(value['env'].items()):
        lines.append('export ' + variable + '=' + quoted(container_value(name, item)))
    for entry in reversed(container_paths(name, value)):
        lines.append('export PATH=' + quoted(entry) + ':"$PATH"')
    return '\n'.join(lines) + '\n'


def closure(names, toolchains):
    """Required toolchains in dependency order, each once."""
    ordered = []

    def visit(name, path):
        if name in path:
            raise SetupError('toolchain requires form a cycle: ' + ' -> '.join((*path, name)))
        if name in ordered:
            return
        if name not in toolchains:
            raise SetupError('required toolchain is missing: ' + name)
        for required in toolchains[name]['requires']:
            visit(required, (*path, name))
        ordered.append(name)
    for name in sorted(names):
        visit(name, ())
    return ordered


# Extraction

def extract(archive, destination, strip, prefix=''):
    """Extract a tar stream member by member without leaving the destination.

    With a prefix, only the members below that archive directory are extracted,
    relative to it. Returns the number of extracted members.
    """
    destination = Path(destination)
    root = destination.resolve()
    selected = prefix.split('/') if prefix else []
    count = 0

    def inside(path):
        resolved = Path(os.path.realpath(path))
        return resolved == root or root in resolved.parents

    def target_of(member_name):
        name = member_name
        while name.startswith('./'):
            name = name[2:]
        parts = [part for part in name.split('/') if part not in ('', '.')]
        if member_name.startswith('/') or '..' in parts:
            raise SetupError('unsafe toolchain member: ' + member_name)
        if selected:
            if parts[:len(selected)] != selected:
                return None
            parts = parts[len(selected):]
        else:
            parts = parts[strip:]
        return destination.joinpath(*parts) if parts else None

    for member in archive:
        target = target_of(member.name)
        if target is None:
            continue
        count += 1
        if not inside(target.parent) or target.is_symlink():
            raise SetupError('unsafe toolchain member: ' + member.name)
        if member.isdir():
            target.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(target, 0o755)
        elif member.isreg():
            target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            source = archive.extractfile(member)
            with open(target, 'xb') as handle:
                shutil.copyfileobj(source, handle)
            os.chmod(target, member.mode & 0o755 | 0o400)
        elif member.issym():
            link = member.linkname
            if link.startswith('/') or not inside(target.parent / link):
                raise SetupError('unsafe toolchain member: ' + member.name + ' -> ' + link)
            target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            os.symlink(link, target)
        elif member.islnk():
            linked = target_of(member.linkname)
            if linked is None or not linked.is_file() or linked.is_symlink() or not inside(linked):
                raise SetupError('unsafe toolchain member: ' + member.name + ' links to ' + member.linkname)
            target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            os.link(linked, target)
        else:
            raise SetupError('unsafe toolchain member type: ' + member.name)
    return count


def archive_label(source):
    return source['url'] if 'url' in source else Path(source['archive']).name


def tls_context(env):
    """The host CA bundle that setup saved when host CA trust is on, else the system trust."""
    trust = env.get(PROFILE.env('TRUST_HOST_CA'), '').lower()
    if trust in ('', '0', 'false', 'no'):
        return ssl.create_default_context()
    if trust not in ('1', 'true', 'yes'):
        raise SetupError(PROFILE.env('TRUST_HOST_CA') + ' must be 0, 1, true, false, yes, or no')
    bundle = env.get(PROFILE.env('CA_BUNDLE'), '') or next((c for c in CA_CANDIDATES if Path(c).is_file()), '')
    if not bundle or not Path(bundle).is_file():
        raise SetupError('no CA bundle file found for host CA trust; set ' + PROFILE.env('CA_BUNDLE') +
                         ' to a bundle file')
    try:
        return ssl.create_default_context(cafile=bundle)
    except (OSError, ssl.SSLError) as error:
        raise SetupError('Cannot load the CA bundle ' + bundle + ': ' + str(error)) from None


class HttpsOnlyRedirects(urllib.request.HTTPRedirectHandler):
    """Follow redirects only to https URLs without credentials."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not https_url(newurl, limit=8192):
            raise SetupError('Refused the redirect of ' + req.full_url + ' to a URL that is not https')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url, env):
    """Open one https download; proxies come from the host environment as usual."""
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=tls_context(env)),
                                         HttpsOnlyRedirects())
    response = opener.open(urllib.request.Request(url, headers={'User-Agent': 'sandbox-toolchains'}),
                           timeout=DOWNLOAD_TIMEOUT)
    if response.status != 200:
        response.close()
        raise SetupError('Cannot download ' + url + ': HTTP status ' + str(response.status))
    length = response.headers.get('Content-Length', '')
    if length.isdigit() and int(length) > DOWNLOAD_LIMIT:
        response.close()
        raise SetupError('Cannot download ' + url + f': larger than {DOWNLOAD_LIMIT} bytes')
    return response


def open_archive(source, env):
    if 'url' not in source:
        return open(source['archive'], 'rb')
    print('Downloading ' + source['url'], flush=True)
    return download(source['url'], env)


def verified_copy(source, library, env):
    """A private copy of one archive in the library, hashed while it is written.

    Downloads land here, and extraction reads only this copy, so a local archive
    that another process can change (even inside a workspace) cannot differ from
    the checked bytes.
    """
    descriptor, name = tempfile.mkstemp(prefix='.download-', dir=library)
    copy = Path(name)
    digest = hashlib.sha256()
    size = 0
    try:
        with open(descriptor, 'wb') as output, open_archive(source, env) as handle:
            for block in iter(lambda: handle.read(1 << 20), b''):
                size += len(block)
                if size > DOWNLOAD_LIMIT:
                    raise SetupError('Cannot read ' + archive_label(source) + f': larger than {DOWNLOAD_LIMIT} bytes')
                digest.update(block)
                output.write(block)
        if digest.hexdigest() != source['sha256']:
            raise SetupError('archive SHA-256 mismatch for ' + archive_label(source) + ': ' + digest.hexdigest())
    except (OSError, http.client.HTTPException) as error:
        copy.unlink(missing_ok=True)
        reason = getattr(error, 'reason', error)
        hint = ''
        if isinstance(reason, ssl.SSLCertVerificationError):
            hint = '; on a network that re-signs TLS, enable host CA trust with --container-setup'
        verb = 'download' if 'url' in source else 'read'
        raise SetupError('Cannot ' + verb + ' ' + archive_label(source) + ': ' + str(error) + hint) from None
    except BaseException:
        copy.unlink(missing_ok=True)
        raise
    return copy


@contextlib.contextmanager
def archive_copies(library, env):
    """Verified copies keyed by SHA-256, so each archive is fetched once per command."""
    copies = {}

    def get(source):
        if source['sha256'] not in copies:
            copies[source['sha256']] = verified_copy(source, library, env)
        return copies[source['sha256']]
    try:
        yield get
    finally:
        for copy in copies.values():
            copy.unlink(missing_ok=True)


def extract_archive(source, destination, copy):
    try:
        with tarfile.open(copy, 'r:*') as members:
            count = extract(members, destination, source.get('strip_components', 0), source.get('path', ''))
    except (OSError, tarfile.TarError) as error:
        raise SetupError('Cannot extract ' + archive_label(source) + ': ' + str(error)) from None
    if source.get('path') and not count:
        raise SetupError('path ' + source['path'] + ' not found in ' + archive_label(source))
    record = {'url': source['url']} if 'url' in source else {'archive': Path(source['archive']).name}
    record['sha256'] = source['sha256']
    if source.get('path'):
        record['path'] = source['path']
    return record


def merge(part, root, target):
    """Move one extracted source below root/target; a path two sources create fails."""
    def overlap_error(path):
        return SetupError('toolchain sources overlap at ' + str(path.relative_to(root)) +
                          '; each file must come from one source')

    def move_children(directory, destination):
        for item in sorted(directory.iterdir()):
            moved = destination / item.name
            if item.is_dir() and not item.is_symlink():
                if not os.path.lexists(moved):
                    os.rename(item, moved)
                elif moved.is_dir() and not moved.is_symlink():
                    move_children(item, moved)
                else:
                    raise overlap_error(moved)
            elif os.path.lexists(moved):
                raise overlap_error(moved)
            else:
                os.rename(item, moved)

    destination = root
    for name in target.split('/') if target else ():
        destination = destination / name
        if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
            raise overlap_error(destination)
        if not destination.exists():
            destination.mkdir(mode=0o755)
            os.chmod(destination, 0o755)
    move_children(part, destination)


def extract_sources(recipe, root, library, env):
    """Extract every source in order into root; returns one provenance record each."""
    records = []
    with archive_copies(library, env) as copies:
        for source in recipe['sources']:
            part = Path(tempfile.mkdtemp(prefix='.staging-part-', dir=library))
            try:
                if 'image' in source:
                    record = extract_image(source, part)
                else:
                    record = extract_archive(source, part, copies(source))
                merge(part, root, source['target'])
            finally:
                shutil.rmtree(part, ignore_errors=True)
            if source['target']:
                record['target'] = source['target']
            records.append(record)
    return records


def extract_image(source, destination):
    image = source['image']
    present = run(['image', 'exists', image])
    if present.returncode == 1:
        # A digest-pinned pull runs no code, so it needs no maintenance consent;
        # builds still do (design D1).
        print('Pulling ' + image, flush=True)
        pulled = run(['pull', image])
        if pulled.returncode != 0:
            detail = pulled.stderr.strip()[-400:]
            raise SetupError('Cannot pull ' + image + (': ' + detail if detail else ''))
    elif present.returncode != 0:
        raise SetupError('Cannot inspect ' + image)
    inspected = run(['image', 'inspect', '--format', '{{.Id}}', image])
    if inspected.returncode != 0:
        raise SetupError('Cannot inspect ' + image)
    created = run(['create', '--network=none', '--pull=never', '--entrypoint', '/sandbox-toolchain-copy', image])
    container = created.stdout.strip()
    if created.returncode != 0 or not SHA256.fullmatch(container):
        raise SetupError('Cannot create a copy container for ' + image)
    try:
        with stream(['cp', container + ':' + source['path'], '-']) as output:
            try:
                with tarfile.open(fileobj=output, mode='r|*') as members:
                    extract(members, destination, 1)
            except tarfile.TarError as error:
                raise SetupError('Cannot extract ' + source['path'] + ' from ' + image + ': ' + str(error)) from None
    finally:
        run(['rm', '--force', container])
    return {'image': image, 'path': source['path'], 'image_id': inspected.stdout.strip()}


# Verification

def runtime_image(env):
    image = env.get(PROFILE.env('IMAGE')) or PROFILE.image('agent', 'latest')
    present = run(['image', 'exists', image])
    if present.returncode != 0:
        raise SetupError('The runtime image ' + image + ' is missing; prepare it with --container-setup '
                         'or --container-build first.')
    inspected = run(['image', 'inspect', '--format', '{{.Id}}', image])
    return image, inspected.stdout.strip()


def check(library, name, root, value, toolchains, image):
    mounts = []
    for required in closure(value['requires'], toolchains):
        mounts += ['--volume', str(Path(library) / required) + ':' + MOUNT + '/' + required + ':ro,nosuid,nodev']
    mounts += ['--volume', str(root) + ':' + MOUNT + '/' + name + ':ro,nosuid,nodev']
    # Start in /: the engine must never create or chown the image's WORKDIR.
    result = run(['run', '--rm', '--network=none', '--read-only', '--pull=never', '--userns=keep-id', '--workdir', '/',
                  '--user', f'{os.getuid()}:{os.getgid()}', '--cap-drop=all', '--security-opt=no-new-privileges',
                  '--tmpfs', '/tmp:rw,nosuid,nodev,noexec,size=256m',
                  '--mount', 'type=tmpfs,destination=' + MOUNT + ',tmpfs-size=1m', *mounts,
                  '--entrypoint', '/bin/sh', image, '-c', '. ' + MOUNT + '/' + name + '/env.sh && exec "$@"', 'sh',
                  *value['check']], timeout=CHECK_TIMEOUT)
    if result.returncode != 0:
        output = (result.stdout + result.stderr).strip()[-4000:]
        raise SetupError(f'toolchain check failed for {name} (status {result.returncode}): ' + shlex.join(value['check']) +
                         ('\n' + output if output else ''))


def verified_record(image_id):
    return {'base': base_reference(INSTALLATION), 'date': time.strftime('%Y-%m-%d', time.gmtime()),
            'runtime_image': image_id}


# Library operations

def publish(library, name, staging):
    final = library / name
    old = None
    if final.exists():
        old = Path(tempfile.mkdtemp(prefix='.old-' + name + '-', dir=library))
        os.rmdir(old)
        os.rename(final, old)
    os.rename(staging, final)
    render(library)
    if old:
        shutil.rmtree(old)


def add(library, argument, env):
    """Install a catalog recipe by name, or an operator recipe file."""
    recipe = resolve_recipe(argument, env)
    name = recipe['name']
    library = prepare_library(library, avoid=(INSTALLATION, *state_directories(env)))
    with locked(library):
        toolchains = installed(library)
        others = {key: item for key, item in toolchains.items() if key != name}
        for required in recipe['requires']:
            if required not in others:
                raise SetupError('required toolchain is missing: ' + required)
        closure(recipe['requires'], {**others, name: recipe})
        for key in others:
            try:
                closure([key], {**others, name: recipe})
            except SetupError as error:
                raise SetupError('toolchain requires form a cycle through ' + key + ': ' + str(error)) from None
        if recipe['default']:
            for required in closure(recipe['requires'], others):
                if not others[required]['default']:
                    raise SetupError('default toolchain ' + name + ' requires non-default ' + required +
                                     '; set default to false or make ' + required + ' a default toolchain')
        staging = Path(tempfile.mkdtemp(prefix='.staging-' + name + '-', dir=library))
        try:
            records = extract_sources(recipe, staging, library, env)
            provided = commands(staging, recipe['path'])
            if recipe['default']:
                for key, other in others.items():
                    if not other['default']:
                        continue
                    shared = sorted(set(provided) & set(other['commands']))
                    variables = sorted(set(recipe['env']) & set(other['env']))
                    if shared or variables:
                        raise SetupError('default toolchain ' + name + ' conflicts with default ' + key + ' on ' +
                                         ', '.join(shared + variables) + '; set default to false in one of them')
            image, image_id = runtime_image(env)
            (staging / 'env.sh').write_text(env_script(name, recipe))
            os.chmod(staging / 'env.sh', 0o644)
            check(library, name, staging, recipe, others, image)
            # The manifest keeps every key that older wrappers read (design D3);
            # 'source' lists provenance records, never host paths of the recipe.
            manifest = {key: item for key, item in recipe.items() if key != 'sources'}
            manifest.update(source=records, commands=provided, verified=verified_record(image_id))
            write_atomic(staging / 'toolchain.json', json.dumps(manifest, indent=2, sort_keys=True) + '\n')
            os.chmod(staging, 0o755)
            publish(library, name, staging)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    return library / name


def remove(library, name, env=None):
    library = prepare_library(library, avoid=(INSTALLATION, *state_directories(env or os.environ)))
    with locked(library):
        toolchains = installed(library)
        if name not in toolchains:
            raise SetupError('toolchain is not installed: ' + name)
        dependents = sorted(key for key, item in toolchains.items() if name in item['requires'])
        if dependents:
            raise SetupError('toolchain ' + name + ' is required by ' + ', '.join(dependents) + '; remove them first')
        old = Path(tempfile.mkdtemp(prefix='.old-' + name + '-', dir=library))
        os.rmdir(old)
        os.rename(library / name, old)
        render(library)
        shutil.rmtree(old)


def verify(library, name, env):
    library = prepare_library(library, avoid=(INSTALLATION, *state_directories(env)))
    with locked(library):
        toolchains = installed(library)
        if name and name not in toolchains:
            raise SetupError('toolchain is not installed: ' + name)
        image, image_id = runtime_image(env)
        for key in ([name] if name else sorted(toolchains)):
            value = toolchains[key]
            others = {other: item for other, item in toolchains.items() if other != key}
            check(library, key, library / key, value, others, image)
            value['verified'] = verified_record(image_id)
            write_atomic(library / key / 'toolchain.json', json.dumps(value, indent=2, sort_keys=True) + '\n')
        render(library)


def entry(name, value):
    return {'name': name, 'version': value['version'], 'default': value['default'], 'commands': value['commands'],
            'path': container_paths(name, value),
            'env': {variable: container_value(name, item) for variable, item in sorted(value['env'].items())},
            'requires': value['requires'], 'notes': value['notes'], 'check': value['check'],
            'source': value['source'], 'verified': {'base': value['verified']['base'],
                                                    'date': value['verified']['date']}}


GUIDE = """# Toolchains

The toolchains under /toolchains are provided by the operator and are read-only.
Do not install toolchains or system packages yourself. If a needed toolchain is
missing, ask the operator to add it. Package downloads (for example Maven, npm,
pip, Cargo or Go modules) may be blocked by the network policy.

To use a toolchain in one command, source its env.sh first:

    . /toolchains/<name>/env.sh && <command>

Default toolchains are also on PATH, after the system tools, in sessions started
after they were added. Toolchains added during a session are available only
through their env.sh or full paths until the next session.
"""


def render(library):
    library = Path(library)
    entries = [entry(name, value) for name, value in installed(library).items()]
    lines = [GUIDE]
    if not entries:
        lines.append('No toolchains are installed.\n')
    for item in entries:
        env_text = ', '.join(variable + '=' + value for variable, value in item['env'].items()) or 'none'
        lines.append('## ' + item['name'] + ' ' + item['version'] + '\n')
        lines.append('- Use: `. /toolchains/' + item['name'] + '/env.sh && ' + shlex.join(item['check']) + '`')
        lines.append('- Commands: ' + (', '.join(item['commands']) or 'none'))
        lines.append('- Environment: ' + env_text)
        lines.append('- Requires: ' + (', '.join(item['requires']) or 'none'))
        lines.append('- Default on PATH in new sessions: ' + ('yes' if item['default'] else 'no'))
        for note in item['notes']:
            lines.append('- Note: ' + note)
        lines.append('- Verified on ' + item['verified']['base'] + ' (' + item['verified']['date'] + ')\n')
    write_atomic(library / 'toolchains.md', '\n'.join(lines))
    write_atomic(library / 'index.json', json.dumps({'schema': SCHEMA, 'toolchains': entries}, indent=2) + '\n')


def launch_env(library, base):
    """Default toolchains verified on base: PATH entries first, then variables."""
    index = json.loads((Path(library) / 'index.json').read_text())
    if index.get('schema') != SCHEMA or not isinstance(index.get('toolchains'), list):
        raise SetupError('Invalid toolchain index; run --container-toolchain verify.')
    by_name = {item['name']: item for item in index['toolchains']}
    selected, warnings = [], []
    for item in index['toolchains']:
        if not item['default']:
            continue
        if item['verified']['base'] != base:
            warnings.append('toolchain ' + item['name'] + ' was verified on another base image; it gets no default '
                            'environment until --container-toolchain verify ' + item['name'] + ' succeeds')
            continue
        selected.append(item['name'])
    ordered = [name for name in closure(selected, by_name) if name in selected]
    lines = []
    for name in ordered:
        lines += [('path', path) for path in by_name[name]['path']]
    for name in ordered:
        for variable, value in by_name[name]['env'].items():
            if not ENV_NAME.fullmatch(variable) or neutral_protected(variable) or not control_free(value) \
                    or '\t' in value:
                raise SetupError('Invalid toolchain environment in the index: ' + variable)
            if profile_protected(variable):
                warnings.append('toolchain ' + name + ' sets ' + variable + ', which this wrapper protects; '
                                'it is left out of this session')
                continue
            lines.append(('env', variable, value))
    return lines, warnings


def size(path):
    return sum(item.lstat().st_size for item in Path(path).rglob('*'))


def listing(library, env):
    """Installed toolchains, then the catalog recipes that are not installed."""
    library = prepare_library(library, avoid=(INSTALLATION, *state_directories(env)))
    toolchains = installed(library)
    lines = ['Toolchain library: ' + str(library)]
    if not toolchains:
        lines.append('No toolchains are installed.')
    for name, value in toolchains.items():
        lines.append(f"{name}\t{value['version']}\tdefault={'yes' if value['default'] else 'no'}\t"
                     f"{size(library / name) // (1 << 20)} MiB\trequires={','.join(value['requires']) or '-'}\t"
                     f"verified={value['verified']['base']} {value['verified']['date']}")
    available = {name: recipe for name, recipe in catalog().items() if name not in toolchains}
    if available:
        lines.append('Available in the catalog (add <name>):')
    for name, recipe in available.items():
        lines.append(f"{name}\t{recipe['version']}\tdefault={'yes' if recipe['default'] else 'no'}\t"
                     f"requires={','.join(recipe['requires']) or '-'}\tavailable")
    return lines


def main(argv):
    env = os.environ
    if not argv:
        raise SetupError('usage: --container-toolchain add <recipe.json|name> | list | remove <name> | verify [<name>]')
    operation, args = argv[0], argv[1:]
    if operation == 'launch-env':
        library, avoid = None, []
        while args:
            if len(args) < 2 or args[0] not in ('--library', '--avoid'):
                raise SetupError('launch-env takes --library PATH and --avoid PATH options')
            if args[0] == '--library':
                library = Path(args[1])
            else:
                avoid.append(Path(args[1]))
            args = args[2:]
        library = prepare_library(library or library_path(env), avoid=(INSTALLATION, *avoid))
        if not (library / 'index.json').exists():
            with locked(library):
                if not (library / 'index.json').exists():
                    render(library)
        lines, warnings = launch_env(library, base_reference(INSTALLATION))
        for warning in warnings:
            print(PREFIX + warning, file=sys.stderr)
        print('library\t' + str(library))
        for line in lines:
            print('\t'.join(line))
        return 0
    library = library_path(env)
    if operation == 'add' and len(args) == 1:
        path = add(library, args[0], env)
        print('Added toolchain ' + path.name + ' to ' + str(library))
    elif operation == 'remove' and len(args) == 1:
        remove(library, args[0], env)
        print('Removed toolchain ' + args[0])
    elif operation == 'verify' and len(args) <= 1:
        verify(library, args[0] if args else None, env)
        print('Verified ' + (args[0] if args else 'all toolchains'))
    elif operation == 'list' and not args:
        print('\n'.join(listing(library, env)))
    else:
        raise SetupError('usage: --container-toolchain add <recipe.json|name> | list | remove <name> | verify [<name>]')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except SetupError as error:
        print(PREFIX + str(error), file=sys.stderr)
        sys.exit(1)
