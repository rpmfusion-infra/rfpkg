# -*- coding: utf-8 -*-
# cli.py - a cli client class module for rfpkg
#
# Copyright (C) 2011 Red Hat Inc.
# Author(s): Jesse Keating <jkeating@redhat.com>
#            Nicolas Chauvet <kwizart@gmail.com> - 2015
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
# the full text of the license.

from __future__ import print_function

import argparse
import sys
import os
import logging
import six

if six.PY3:
    import rfpkgdb2client
else:
    import pkgdb2client as rfpkgdb2client

from pyrpkg.cli import cliClient

RELEASE_BRANCH_REGEX = r'^(f\d+|el\d+|epel\d+)$'
LOCAL_PACKAGE_CONFIG = 'package.cfg'

class rfpkgClient(cliClient):
    def __init__(self, config, name=None):
        self.DEFAULT_CLI_NAME = 'rfpkg'
        super(rfpkgClient, self).__init__(config, name)
        self.setup_completers()

    def load_cmd(self):
        super().load_cmd()

        distgit_namespaces = []
        distgit_namespaced = self._get_bool_opt('distgit_namespaced')
        if distgit_namespaced and self.config.has_option(self.name, 'distgit_namespaces'):
            distgit_namespaces = self.config.get(self.name, 'distgit_namespaces').split()
        self._cmd.distgit_namespaces = distgit_namespaces

    def setup_argparser(self):
        super(rfpkgClient, self).setup_argparser()

        # This line is added here so that it shows up with the "--help" option,
        # but it isn't used for anything else
        self.parser.add_argument(
            '--user-config', help='Specify a user config file to use')
        opt_release = self.parser._option_string_actions['--release']
        opt_release.help = 'Override the discovered release, e.g. f25, which has to match ' \
                           'the remote branch name created in package repository. ' \
                           'Particularly, use master to build RPMs for rawhide.'

    def retire(self):
        try:
            repo_name = self.cmd.repo_name
            ns_repo_name = self.cmd.ns_repo_name
            namespace = ns_repo_name.split(repo_name)[0].rstrip('/')
            # Skip if package is already retired to allow to retire only in
            # pkgdb
            if os.path.isfile(os.path.join(self.cmd.path, 'dead.package')):
                self.log.warn('dead.package found, package probably already '
                              'retired - will not remove files from git or '
                              'overwrite existing dead.package file')
            else:
                self.cmd.retire(self.args.reason)
                self.push()

            branch = self.cmd.branch_merge
            pkgdb = rfpkgdb2client.PkgDB(
                login_callback=rfpkgdb2client.ask_password, url="https://admin.rpmfusion.org/pkgdb")
            pkgdb.retire_packages(repo_name, branch, namespace=namespace)
        except Exception as e:
            self.log.error('Could not retire package: %s' % e)
            sys.exit(1)


