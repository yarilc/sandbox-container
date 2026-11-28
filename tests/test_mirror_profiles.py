"""Mirror profile parsing and host library operations with synthetic inputs."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from sandbox_profile import ROOT, env as setting, test_setting

sys.path.insert(0, str(ROOT / 'setup'))
import mirrors  # noqa: E402
from common import MANIFEST, MIRROR_CATALOG, SetupError  # noqa: E402
from mirror_policy import profile  # noqa: E402
from policy import PolicyError  # noqa: E402


def sample(name='local', **options):
    return {'schema': 1, 'name': name, 'revision': '1', 'default': False,
            'upstreams': [{'id': 'base', 'ecosystem': 'rpm',
                           'base_url': 'https://packages.test/rpm/', **options}]}


class ProfileTests(unittest.TestCase):
    def test_normalizes_https_prefix(self):
        value = profile(sample(base_url='https://PACKAGES.test:443/rpm'))
        self.assertEqual(value['upstreams'][0]['base_url'], 'https://packages.test/rpm/')

    def test_rejects_unsupported_or_ambiguous_upstreams(self):
        invalid = ({'ecosystem': 'unknown'}, {'username': 'user'},
                   {'base_url': 'http://packages.test/rpm/'},
                   {'base_url': 'https://user:password@packages.test/rpm/'},
                   {'base_url': 'https://packages.test/rpm/%2e/'},
                   {'base_url': 'https://packages.test/rpm/../web/'},
                   {'base_url': 'https://packages.test/rpm/?allow=all'},
                   {'base_url': 'https://packages.test:0/rpm/'},
                   {'addresses': ['169.254.169.254']},
                   {'ecosystem': 'go'})
        for extra in invalid:
            with self.subTest(extra=extra), self.assertRaises(PolicyError):
                profile(sample(**extra))

    def test_local_addresses_are_explicit_and_catalog_is_public(self):
        value = sample(addresses=['192.168.2.3', 'fd00::3'])
        self.assertEqual(profile(value)['upstreams'][0]['addresses'], ['192.168.2.3', 'fd00::3'])
        with self.assertRaises(PolicyError):
            profile(value, catalog=True)

    def test_split_prefixes_are_validated_independently(self):
        value = sample(artifact_bases=[{'base_url': 'https://storage.test/packages/', 'addresses': ['192.168.5.2']}])
        self.assertEqual(profile(value)['upstreams'][0]['artifact_bases'][0]['addresses'], ['192.168.5.2'])
        with self.assertRaises(PolicyError):
            profile(value, catalog=True)
        for url in ('https://packages.test/rpm/', 'https://storage.test/rpm/nested/', 'https://storage.test/'):
            with self.subTest(url=url), self.assertRaises(PolicyError):
                profile(sample(artifact_bases=[{'base_url': url}]))


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=test_setting('TEST_TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.project = self.base / 'worktree' / 'project'
        self.project.mkdir(parents=True)
        self.catalog = self.base / 'catalog'
        self.catalog.mkdir()
        self.state = self.base / 'state'
        self.state.mkdir()
        self.env = {'HOME': str(self.base / 'home'), setting('STATE_DIR'): str(self.state)}
        self.library = mirrors.library_path(self.env)
        previous = Path.cwd()
        os.chdir(self.project)
        self.addCleanup(os.chdir, previous)
        patcher = patch.object(mirrors, 'CATALOG', self.catalog)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, path, value):
        path.write_text(json.dumps(value))
        return path

    def run_command(self, *args):
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(mirrors.main(list(args), self.env), 0)
        return output.getvalue()

    def test_catalog_list_add_and_remove(self):
        self.write(self.catalog / 'public.json', sample('public') | {'default': True})
        self.assertIn('public\tavailable', self.run_command('list'))
        self.assertFalse(self.library.exists())
        self.run_command('add', 'public')
        self.assertEqual(self.library.stat().st_mode & 0o777, 0o700)
        self.assertIn('public\t1\tdefault=yes\tinstalled', self.run_command('list'))
        self.run_command('remove', 'public')
        self.assertIn('public\tavailable', self.run_command('list'))

    def test_release_catalog_uses_reviewed_public_rpm_prefixes(self):
        self.assertLessEqual(set(MIRROR_CATALOG), set(MANIFEST))
        for relative in MIRROR_CATALOG:
            path = ROOT / relative
            (self.catalog / path.name).write_bytes(path.read_bytes())
        available = mirrors.profiles(self.catalog, catalog=True)
        self.assertEqual(set(available), {'rocky9', 'al2023'})
        self.assertEqual([item['id'] for item in available['rocky9']['upstreams']], ['baseos', 'appstream', 'extras'])
        self.assertEqual(available['al2023']['revision'], '2023.12.20261120-x86_64')
        self.assertEqual(available['al2023']['upstreams'][0]['artifact_bases'],
                         [{'base_url': 'https://cdn.amazonlinux.com/al2023/blobstore/'}])

    def test_invalid_replacement_preserves_installed_profile(self):
        source = self.write(self.base / 'local.json', sample())
        self.run_command('add', os.path.relpath(source))
        installed = self.library / 'local.json'
        original = installed.read_bytes()
        source.write_text('{"schema": 1, "schema": 2}')
        with self.assertRaises(PolicyError):
            self.run_command('add', str(source))
        self.assertEqual(installed.read_bytes(), original)
        self.write(source, sample() | {'revision': '2'})
        self.run_command('add', str(source))
        self.assertIn('local\t2', self.run_command('list'))
        self.assertFalse(list(self.library.glob('.write-*')))

    def test_refuses_writable_mounts_and_symlink_aliases(self):
        source = self.write(self.base / 'safe.json', sample())
        alias = self.project / 'alias.json'
        alias.symlink_to(source)
        source_in_state = self.write(self.state / 'local.json', sample())
        outside_alias = self.base / 'alias.json'
        outside_alias.symlink_to(source_in_state)
        sibling_source = self.write(self.project.parent / 'local.json', sample())
        with patch.object(mirrors, 'saved_worktree_scope', return_value=True):
            for path in (alias, outside_alias, sibling_source):
                with self.subTest(path=path), self.assertRaisesRegex(SetupError, 'writable workspace or state'):
                    self.run_command('add', str(path))
        self.assertFalse(self.library.exists())

    def test_refuses_library_inside_workspace(self):
        self.env['XDG_DATA_HOME'] = str(self.project)
        source = self.write(self.base / 'safe.json', sample())
        with self.assertRaisesRegex(SetupError, 'writable workspace or state'):
            self.run_command('add', str(source))
        self.assertFalse(mirrors.library_path(self.env).exists())

    def test_snapshot_keeps_defaults_and_explicit_order_after_library_edits(self):
        for name in ('z-default', 'a-default', 'project-only', 'toolchain-only'):
            source = self.write(self.base / (name + '.json'), sample(name) | {'default': name.endswith('-default')})
            self.run_command('add', str(source))
        self.write(self.project / mirrors.SELECTION,
                   {'profiles': ['project-only', 'a-default', 'project-only', 'unknown']})
        mounts = [self.project, self.state]
        with redirect_stderr(io.StringIO()) as diagnostics:
            snapshot = mirrors.selection_snapshot(self.project, mounts, ['toolchain-only'], self.env)
        self.assertEqual(list(snapshot['profiles']), ['a-default', 'z-default', 'project-only', 'toolchain-only'])
        self.assertIn('profile unknown is not installed', diagnostics.getvalue())
        self.assertIn('mirror profile=project-only revision=1 ', diagnostics.getvalue())
        self.run_command('remove', 'project-only')
        self.assertIn('project-only', snapshot['profiles'])
        with redirect_stderr(io.StringIO()):
            after = mirrors.selection_snapshot(self.project, mounts, [], self.env)
        self.assertNotIn('project-only', after['profiles'])

    def test_selection_rejects_unsafe_or_malformed_workspace_files(self):
        path = self.project / mirrors.SELECTION
        for contents in ('{"profiles": [], "profiles": []}', '{"profiles": ["https://packages.test/"]}',
                         '{"profiles": [], "other": []}', ' ' * 8193):
            with self.subTest(contents=contents[:80]), self.assertRaisesRegex(SetupError, mirrors.SELECTION):
                path.write_text(contents)
                mirrors.workspace_selection(self.project)
        path.unlink()
        source = self.write(self.base / 'outside.json', {'profiles': []})
        path.symlink_to(source)
        with self.assertRaisesRegex(SetupError, 'regular JSON file'):
            mirrors.workspace_selection(self.project)

    def test_verify_reports_each_upstream_and_partial_failure(self):
        value = sample()
        value['upstreams'].append(value['upstreams'][0] | {'id': 'other'})
        self.run_command('add', str(self.write(self.base / 'local.json', value)))
        with patch.object(mirrors, 'Client') as factory, redirect_stdout(io.StringIO()) as output:
            factory.return_value.verify = AsyncMock(side_effect=[None, mirrors.Rejected('unsafe-address')])
            status = mirrors.main(['verify', 'local'], self.env)
        self.assertEqual(status, 1)
        self.assertIn('local base verified', output.getvalue())
        self.assertIn('local other failed unsafe-address', output.getvalue())

    def test_windows_drive_operator_profiles_and_boundaries(self):
        drive = self.base / 'win-c'
        entry = drive / 'entry'
        win_worktree = drive / 'worktree'
        win_project = win_worktree / 'project'
        profiles_dir = drive / 'profiles'
        for directory in (drive, entry, win_worktree, win_project, profiles_dir):
            directory.mkdir(parents=True, exist_ok=True)
            directory.chmod(0o777)

        explicit = self.write(profiles_dir / 'explicit.json', sample('explicit'))
        relative = self.write(profiles_dir / 'relative.json', sample('relative'))
        inside_ws = self.write(win_project / 'inside.json', sample('inside'))
        sibling_wt = self.write(win_worktree / 'sibling.json', sample('sibling'))
        inside_entry = self.write(entry / 'inside-entry.json', sample('inside-entry'))
        for file_path in (explicit, relative, inside_ws, sibling_wt, inside_entry):
            file_path.chmod(0o777)

        win_link = profiles_dir / 'alias.json'
        win_link.symlink_to(explicit)
        native_link = self.base / 'native-alias.json'
        native_link.symlink_to(explicit)

        unmounted = self.base / 'world-writable'
        unmounted.mkdir()
        unmounted.chmod(0o777)
        unmounted_file = self.write(unmounted / 'other.json', sample('other'))
        unmounted_file.chmod(0o777)

        win_env = self.env | {mirrors.WINDOWS_ENTRY: str(entry)}
        previous_cwd = Path.cwd()
        os.chdir(win_project)
        self.addCleanup(os.chdir, previous_cwd)

        with patch.object(mirrors.toolchains, 'drive_mounts', return_value={'c': str(drive)}):
            # (a) Explicit Windows drive path and relative path on drvfs succeed into the 0o700 native library.
            with redirect_stdout(io.StringIO()):
                self.assertEqual(mirrors.main(['add', r'C:\profiles\explicit.json'], win_env), 0)
                self.assertEqual(mirrors.main(['add', '../../profiles/relative.json'], win_env), 0)
            self.assertEqual(self.library.stat().st_mode & 0o777, 0o700)
            self.assertTrue((self.library / 'explicit.json').is_file())
            self.assertTrue((self.library / 'relative.json').is_file())
            self.assertFalse(list(self.library.glob('.write-*')))

            # (b) Overlaps with workspace, widened worktree, state, or Windows entry are refused.
            with patch.object(mirrors, 'saved_worktree_scope', return_value=True):
                for bad in (r'C:\worktree\project\inside.json', r'C:\worktree\sibling.json',
                            r'C:\entry\inside-entry.json', str(self.write(self.state / 'st.json', sample('st')))):
                    with self.subTest(overlap=bad), self.assertRaisesRegex(SetupError, 'writable workspace or state'):
                        mirrors.main(['add', bad], win_env)

            # (b) Symlinks on the Windows drive or pointing into it are refused.
            for link_arg in (r'C:\profiles\alias.json', str(native_link)):
                with self.subTest(symlink=link_arg), self.assertRaisesRegex(SetupError, 'regular file with a protected path'):
                    mirrors.main(['add', link_arg], win_env)

            # (c) Without WINDOWS_ENTRY, or outside mounted Windows drives, 0o777 inputs stay refused.
            with self.assertRaisesRegex(SetupError, 'Unsafe protected path'):
                mirrors.main(['add', str(explicit)], self.env)
            with self.assertRaisesRegex(SetupError, 'Unsafe protected path'):
                mirrors.main(['add', str(unmounted_file)], win_env)

            # (d) The mirror library itself still requires protected native storage.
            bad_lib_env = win_env | {'XDG_DATA_HOME': str(drive / 'lib')}
            with self.assertRaisesRegex(SetupError, 'Unsafe protected path'):
                mirrors.main(['add', r'C:\profiles\explicit.json'], bad_lib_env)
            self.assertFalse((drive / 'lib').exists())
