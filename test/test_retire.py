# -*- coding: utf-8 -*-

import os
import shutil
import unittest
import mock
from six.moves import configparser
import tempfile
import subprocess
import rfpkgdb2client

from rfpkg.cli import rfpkgClient

TEST_CONFIG = os.path.join(os.path.dirname(__file__), 'rfpkg-test.conf')


class RetireTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log = mock.Mock()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _setup_repo(self, origin):
        subprocess.check_call(
            ['git', 'init'],
            cwd=self.tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.check_call(
            ['git', 'config', 'user.name', 'John Doe'],
            cwd=self.tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.check_call(
            ['git', 'config', 'user.email', 'jdoe@example.com'],
            cwd=self.tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.check_call(
            ['git', 'remote', 'add', 'origin', origin],
            cwd=self.tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.check_call(
            ['touch', 'rfpkg.spec'],
            cwd=self.tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.check_call(
            ['git', 'add', '.'],
            cwd=self.tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.check_call(
            ['git', 'commit', '-m', 'Initial commit'],
            cwd=self.tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def _get_latest_commit(self):
        proc = subprocess.Popen(['git', 'log', '-n', '1', '--pretty=%s'],
                                cwd=self.tmpdir, stdout=subprocess.PIPE,
                                universal_newlines=True)
        out, err = proc.communicate()
        return out.strip()

    def _fake_client(self, args):
        config = configparser.SafeConfigParser()
        config.read(TEST_CONFIG)
        with mock.patch('sys.argv', new=args):
            client = rfpkgClient(config)
            client.do_imports(site='rfpkg')
            client.setupLogging(self.log)

            client.parse_cmdline()
            client.args.path = self.tmpdir
            client.cmd.push = mock.Mock()
        return client

    def assertRetired(self, reason):
        self.assertTrue(os.path.isfile(os.path.join(self.tmpdir,
                                                    'dead.package')))
        self.assertFalse(os.path.isfile(os.path.join(self.tmpdir,
                                                     'rfpkg.spec')))
        self.assertEqual(self._get_latest_commit(), reason)

    @mock.patch('rfpkgdb2client.PkgDB')
    def test_retire_with_namespace(self, PkgDB):
        self._setup_repo('ssh://git@pkgs.example.com/rpms/rfpkg')
        args = ['rfpkg', '--release=master', 'retire', 'my reason']

        client = self._fake_client(args)
        client.retire()

        self.assertRetired('my reason')
        self.assertEqual(len(client.cmd.push.call_args_list), 1)
        self.assertEqual(PkgDB.return_value.retire_packages.call_args_list,
                         [mock.call('rfpkg', 'master', namespace='rpms')])

    @mock.patch('rpmfusion_cert.read_user_cert')
    @mock.patch('rfpkgdb2client.PkgDB')
    def test_retire_without_namespace(self, PkgDB, read_user_cert):
        self._setup_repo('ssh://git@pkgs.example.com/rfpkg')
        args = ['rfpkg', '--release=master', 'retire', 'my reason']

        read_user_cert.return_value = 'packager'

        client = self._fake_client(args)
        client.retire()

        self.assertRetired('my reason')
        self.assertEqual(len(client.cmd.push.call_args_list), 1)
        self.assertEqual(PkgDB.return_value.retire_packages.call_args_list,
                         [mock.call('rfpkg', 'master', namespace='rpms')])
