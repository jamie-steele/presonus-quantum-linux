import importlib.util
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/release' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


channels = load('channels')
apt = load('apt_repository')
native = load('build_native')


class ReleaseChannelTests(unittest.TestCase):
    def test_channel_identity_and_debian_upgrade_order(self):
        staging = channels.revision_for_branch('staging', '6', '42')
        stable = channels.revision_for_branch('master', '6', '42')
        self.assertEqual(staging, '6~staging.42')
        self.assertEqual(stable, '6')
        self.assertEqual(channels.channel_for_revision(staging), 'staging')
        self.assertEqual(channels.channel_for_revision(stable), 'master')
        for lower, higher in [('5', staging), (staging, '6~staging.43'), (staging, stable)]:
            subprocess.run(['dpkg', '--compare-versions', lower, 'lt', higher], check=True)

    def test_untrusted_revision_and_branch_names_fail(self):
        for value in ['0', '-1', '6~staging.0', '6~staging.bad', '6;true', '../6']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                channels.channel_for_revision(value)
        with self.assertRaises(ValueError):
            channels.revision_for_branch('feature', '6', '1')

    def test_pinned_tag_and_package_staging_version(self):
        self.assertEqual(channels.pinned_tag(ROOT / 'driver/upstream.lock'),
                         'rfc-20260820.rfc1.s1148921')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'VERSION').write_text('20260820.rfc1.s1148921\n')
            self.assertEqual(native.package_version(root, '6~staging.42')[1],
                             '20260820.rfc1.s1148921-6~staging.42')

    def test_stable_rejects_staging_file_before_metadata_or_signing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            packages = root / 'packages'
            packages.mkdir()
            (packages / 'quantum-dkms_20260820.rfc1.s1148921-6~staging.42_amd64.deb').touch()
            with patch.object(apt, 'run') as command:
                with self.assertRaisesRegex(ValueError, 'cannot enter the stable'):
                    apt.build(packages, root / 'public', 'A' * 40, 'https://example.com', 'stable')
                command.assert_not_called()

    def test_stable_asset_discovery_excludes_staging_before_download(self):
        releases = b'''[[{"tag_name":"rfc-20260820.rfc1.s1148921","draft":false,"assets":[
          {"name":"native-6~staging.42-SHA256SUMS"},
          {"name":"native-6~staging.42-build-evidence.tar.gz"},
          {"name":"quantum-dkms_20260820.rfc1.s1148921-6~staging.42_amd64.deb"}
        ]}]]'''
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(apt, 'run', return_value=releases), patch.object(apt.subprocess, 'run') as fetch:
                apt.download_packages('owner/repo', Path(temporary), 'stable')
                fetch.assert_not_called()

    def test_unknown_suites_fail_closed(self):
        for suite in ['../stable', 'dev', 'Stable']:
            with self.subTest(suite=suite), self.assertRaises(ValueError):
                apt.validate_suite(suite)


@unittest.skipUnless(all(shutil.which(name) for name in ['gpg', 'gpgconf', 'apt-ftparchive', 'apt-get']),
                     'APT signing tools unavailable; hosted APT matrix covers this test')
class SignedChannelIntegrationTests(unittest.TestCase):
    def test_fresh_clients_select_only_their_signed_suite(self):
        with tempfile.TemporaryDirectory(prefix='quantum-channel-test-') as temporary:
            root = Path(temporary)
            key_home = root / 'keys'
            key_home.mkdir(mode=0o700)
            environment = dict(os.environ, GNUPGHOME=str(key_home))
            subprocess.run(['gpg', '--batch', '--pinentry-mode', 'loopback', '--passphrase', '',
                            '--quick-generate-key', 'Disposable channel test <test@example.invalid>',
                            'rsa2048', 'sign', '1d'], env=environment, check=True,
                           capture_output=True)
            try:
                listing = subprocess.check_output(['gpg', '--batch', '--with-colons', '--list-keys'],
                                                  env=environment, text=True, stderr=subprocess.DEVNULL)
                fingerprint = next(line.split(':')[9] for line in listing.splitlines()
                                   if line.startswith('fpr:'))
                versions = {'experimental': '20260820.rfc1.s1148921-6~staging.42',
                            'stable': '20260820.rfc1.s1148921-5'}
                for suite, version in versions.items():
                    payload = root / ('payload-' + suite)
                    (payload / 'DEBIAN').mkdir(parents=True)
                    (payload / 'DEBIAN/control').write_text(
                        f'Package: quantum-dkms\nVersion: {version}\nArchitecture: amd64\n'
                        'Maintainer: Test <test@example.invalid>\nDescription: Never-install test fixture\n')
                    packages = root / 'packages' / suite
                    packages.mkdir(parents=True)
                    subprocess.run(['dpkg-deb', '--build', '--root-owner-group', str(payload),
                                    str(packages / f'quantum-dkms_{version}_amd64.deb')],
                                   check=True, capture_output=True)
                public = root / 'public'
                with patch.dict(os.environ, {'GNUPGHOME': str(key_home)}):
                    apt.snapshot(root / 'packages', public, fingerprint, 'https://example.invalid')
                for suite, version in versions.items():
                    client = root / ('client-' + suite)
                    (client / 'lists/partial').mkdir(parents=True)
                    (client / 'cache').mkdir()
                    (client / 'status').write_text('')
                    sources = client / 'sources.list'
                    sources.write_text(f'deb [signed-by={public}/quantum-archive-keyring.gpg] '
                                       f'file:{public} {suite} main\n')
                    options = ['-o', f'Dir::Etc::sourcelist={sources}', '-o', 'Dir::Etc::sourceparts=-',
                               '-o', f'Dir::State::lists={client}/lists',
                               '-o', f'Dir::State::status={client}/status',
                               '-o', f'Dir::Cache={client}/cache', '-o', 'APT::Update::Error-Mode=any']
                    subprocess.run(['apt-get', *options, 'update'], check=True, capture_output=True)
                    policy = subprocess.check_output(['apt-cache', *options, 'policy', 'quantum-dkms'], text=True)
                    self.assertIn('Candidate: ' + version, policy)
                    if suite == 'stable':
                        self.assertNotIn('~staging', policy)
                self.assertEqual((public / 'quantum.sources').read_bytes(),
                                 (public / 'quantum-staging.sources').read_bytes())
                self.assertIn('Suites: stable', (public / 'quantum-stable.sources').read_text())
            finally:
                subprocess.run(['gpgconf', '--kill', 'gpg-agent'], env=environment,
                               check=False, capture_output=True)


if __name__ == '__main__':
    unittest.main()
