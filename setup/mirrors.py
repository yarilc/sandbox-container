"""Manage and select operator-approved dependency mirror profiles."""

import argparse
import asyncio
import json
import os
from pathlib import Path
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (PROFILE, WINDOWS_ENTRY, SetupError, launcher_paths, private,  # noqa: E402
                    same_or_inside, trusted, writable_mounts)
from toolchains import (WINDOWS_DRIVE, catalog_name, host_ca_bundle, locked, saved_worktree_scope,  # noqa: E402
                        windows_path, write_atomic)
import mirror_policy  # noqa: E402
from mirror import Client, Rejected  # noqa: E402
from policy import PolicyError, fields, revision  # noqa: E402

INSTALLATION = Path(__file__).resolve().parents[1]
CATALOG = INSTALLATION / 'setup/mirror-catalog'
LIBRARY = 'sandbox-mirrors'
SELECTION = '.sandbox-mirrors.json'
USAGE = 'usage: --container-mirror add <profile.json|name> | list | remove <name> | verify [<name>]'


def library_path(env):
    data = Path(env.get('XDG_DATA_HOME', ''))
    if not data.is_absolute():
        data = Path(env['HOME']) / '.local/share'
    return data / LIBRARY


def outside_mounts(path, mounts):
    physical, links = launcher_paths(path)
    for candidate in (Path(os.path.abspath(path)), physical, *links):
        if any(same_or_inside(candidate, mount) or same_or_inside(mount, candidate) for mount in mounts):
            raise SetupError(f'Mirror path {candidate} overlaps a writable workspace or state mount.')
    for link in links:
        trusted(link)
    return physical


def read_json(path, limit, *, protected=False):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or (protected and info.st_nlink != 1):
            raise SetupError('Mirror input must be a regular file with a protected path.')
        return mirror_policy.decode(handle.read(limit + 1), limit)


def load_profile(path, *, catalog=False):
    path = trusted(path)
    data = read_json(path, mirror_policy.MAX_PROFILE, protected=True)
    return mirror_policy.profile(data, catalog=catalog)


def profiles(directory, *, catalog=False):
    found = {}
    for path in sorted(directory.glob('*.json')):
        if not mirror_policy.is_name(path.stem):
            raise SetupError('Invalid mirror profile filename.')
        if path.is_symlink():
            raise SetupError(f'Mirror profile {path.stem} must be stored as a regular file.')
        value = load_profile(path, catalog=catalog)
        if value['name'] != path.stem:
            raise SetupError(f'Mirror profile filename does not match its name: {path.stem}')
        found[value['name']] = value
    return found


def resolve_profile(argument, env, mounts):
    if env.get(WINDOWS_ENTRY) and (WINDOWS_DRIVE.match(argument) or argument.startswith(('\\\\', '//'))):
        argument = windows_path(argument)
    if catalog_name(argument):
        available = profiles(CATALOG, catalog=True)
        if argument not in available:
            raise SetupError('No catalog mirror profile with that name. Available: ' + (', '.join(available) or 'none'))
        return available[argument]
    path = Path(argument).absolute()
    return load_profile(outside_mounts(path, mounts))


def open_library(env, mounts, *, create=False):
    library = library_path(env)
    outside_mounts(library, mounts)
    return private(library, create=create)


def installed_profiles(library):
    if not library.is_dir():
        return {}
    with locked(library):
        return profiles(library)


def workspace_selection(workspace):
    try:
        value = read_json(Path(workspace) / SELECTION, mirror_policy.MAX_SELECTION)
        fields(value, ('profiles',))
        return mirror_policy.names(value['profiles'])
    except FileNotFoundError:
        return []
    except (OSError, PolicyError, SetupError):
        raise SetupError(f'{SELECTION} must be a bounded, regular JSON file containing only profile names.') from None


def selection_snapshot(workspace, mounts, toolchains, env):
    requested = workspace_selection(workspace)
    installed = installed_profiles(open_library(env, mounts))
    defaults = [name for name, value in installed.items() if value['default']]
    selected = {}
    for name in dict.fromkeys([*defaults, *requested, *toolchains]):
        if name not in installed:
            print(PROFILE.message_prefix + f'Mirror profile {name} is not installed.', file=sys.stderr)
            continue
        value = installed[name]
        selected[name] = value
        print(PROFILE.message_prefix + f'mirror profile={name} revision={revision(value)}', file=sys.stderr)
    return {'schema': 1, 'profiles': selected}


def snapshot_command(argv, env):
    parser = argparse.ArgumentParser(prog='mirror profile selection', add_help=False)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--writable', action='append', type=Path, default=[])
    parser.add_argument('--toolchain', action='append', default=[])
    args = parser.parse_args(argv)
    toolchains = mirror_policy.names(args.toolchain)
    snapshot = selection_snapshot(args.workspace, args.writable, toolchains, env)
    print(json.dumps(snapshot, separators=(',', ':')))
    return 0


async def verify_profiles(installed, name, client):
    if name is not None and name not in installed:
        raise SetupError('Mirror profile is not installed.')
    selected = installed.values() if name is None else (installed[name],)
    status = 0
    for value in selected:
        for upstream in value['upstreams']:
            identifier = f"{value['name']} {upstream['id']}"
            try:
                await client.verify(value, upstream)
            except Rejected as error:
                print(f'{identifier} failed {error}')
                status = 1
            except (OSError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
                print(f'{identifier} failed upstream unavailable')
                status = 1
            else:
                print(f'{identifier} verified')
    return status


def main(argv, env=None):
    env = os.environ if env is None else env
    if not argv:
        raise SetupError(USAGE)
    operation, *args = argv
    if operation == 'snapshot':
        return snapshot_command(args, env)
    mounts = writable_mounts(env, worktree=saved_worktree_scope())
    if operation == 'add' and len(args) == 1:
        value = resolve_profile(args[0], env, mounts)
        library = open_library(env, mounts, create=True)
        with locked(library):
            write_atomic(library / (value['name'] + '.json'), json.dumps(value, indent=2) + '\n')
        print(f"Added mirror profile {value['name']} to {library}")
    elif operation == 'list' and not args:
        library = open_library(env, mounts)
        installed = installed_profiles(library)
        print(f'Mirror library: {library}')
        for name, value in installed.items():
            default = 'yes' if value['default'] else 'no'
            print(f"{name}\t{value['revision']}\tdefault={default}\tinstalled")
        for name in profiles(CATALOG, catalog=True):
            if name not in installed:
                print(f'{name}\tavailable')
    elif operation == 'remove' and len(args) == 1 and mirror_policy.is_name(args[0]):
        library = open_library(env, mounts)
        if not library.is_dir():
            raise SetupError('Mirror profile is not installed.')
        with locked(library):
            path = library / (args[0] + '.json')
            if not path.is_file():
                raise SetupError('Mirror profile is not installed.')
            path.unlink()
        print(f'Removed mirror profile {args[0]}')
    elif operation == 'verify' and (not args or (len(args) == 1 and mirror_policy.is_name(args[0]))):
        library = open_library(env, mounts)
        bundle = host_ca_bundle(env)
        if bundle:
            bundle = trusted(outside_mounts(bundle, mounts))
        return asyncio.run(verify_profiles(installed_profiles(library), args[0] if args else None, Client(bundle or None)))
    else:
        raise SetupError(USAGE)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except (SetupError, PolicyError) as error:
        print(PROFILE.message_prefix + str(error), file=sys.stderr)
        sys.exit(1)
    except OSError as error:
        print(PROFILE.message_prefix + 'Mirror input or library could not be accessed: ' +
              str(error.strerror), file=sys.stderr)
        sys.exit(1)
