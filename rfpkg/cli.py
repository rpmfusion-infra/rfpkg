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
import textwrap

if six.PY3:
    import rfpkgdb2client
else:
    import pkgdb2client as rfpkgdb2client

from pyrpkg.cli import cliClient
from rfpkg.completers import (build_arches, list_targets,
                               rfpkg_packages, distgit_branches)

RELEASE_BRANCH_REGEX = r'^(f\d+|el\d+|epel\d+)$'
LOCAL_PACKAGE_CONFIG = 'package.cfg'

class rfpkgClient(cliClient):
    def __init__(self, config, name=None):
        self.DEFAULT_CLI_NAME = 'rfpkg'
        super(rfpkgClient, self).setup_completers()
        self.setup_completers()
        super(rfpkgClient, self).__init__(config, name)
        self.setup_fed_subparsers()

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

    def setup_fed_subparsers(self):
        """Register the fedora specific targets"""

        # Don't register again the retire command as it is already done
        # by pyrpkg. Starting Python 3.11, it creates an error.
        # https://github.com/python/cpython/pull/18605
        #self.register_retire()

        # Don't register the update command, as rpmfusion does not have a
        # bodhi instance to send update requests to
        #self.register_update()

    def setup_completers(self):
        """
        Set specific argument completers for rfpkg. Structure, where
        are these assignments (name -> method) stored, is in the parent
        class and have to be filled before __init__ (containing argument
        parser definitions) is called there.
        """
        cliClient.set_completer("build_arches", build_arches)
        cliClient.set_completer("list_targets", list_targets)
        cliClient.set_completer("packages", rfpkg_packages)
        cliClient.set_completer("branches", distgit_branches)

    # Target functions go here
    def _format_update_clog(self, clog):
        ''' Format clog for the update template. '''
        lines = [ln for ln in clog.split('\n') if ln]
        if len(lines) == 0:
            return "- Rebuilt.", ""
        elif len(lines) == 1:
            return lines[0], ""
        log = ["# Changelog:"]
        log.append('# - ' + lines[0])
        for ln in lines[1:]:
            log.append('# ' + ln)
        log.append('#')
        return lines[0], "\n".join(log)

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


if __name__ == '__main__':
    client = cliClient()
    client._do_imports()
    client.parse_cmdline()

    if not client.args.path:
        try:
            client.args.path = os.getcwd()
        except:
            print('Could not get current path, have you deleted it?')
            sys.exit(1)

    # setup the logger -- This logger will take things of INFO or DEBUG and
    # log it to stdout.  Anything above that (WARN, ERROR, CRITICAL) will go
    # to stderr.  Normal operation will show anything INFO and above.
    # Quiet hides INFO, while Verbose exposes DEBUG.  In all cases WARN or
    # higher are exposed (via stderr).
    log = client.site.log
    client.setupLogging(log)

    if client.args.v:
        log.setLevel(logging.DEBUG)
    elif client.args.q:
        log.setLevel(logging.WARNING)
    else:
        log.setLevel(logging.INFO)

    # Run the necessary command
    try:
        client.args.command()
    except KeyboardInterrupt:
        pass
