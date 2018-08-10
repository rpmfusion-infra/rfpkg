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

from pyrpkg.cli import cliClient
import sys
import os
import logging
import re
import subprocess
import textwrap
import hashlib

import pkgdb2client


class rfpkgClient(cliClient):
    def __init__(self, config, name=None):
        self.DEFAULT_CLI_NAME = 'rfpkg'
        super(rfpkgClient, self).__init__(config, name)
        self.setup_fed_subparsers()

    def setup_fed_subparsers(self):
        """Register the fedora specific targets"""

        self.register_retire()

    # Target registry goes here
    def register_retire(self):
        """Register the retire target"""

        retire_parser = self.subparsers.add_parser(
            'retire',
            help='Retire a package',
            description='This command will remove all files from the repo, '
                        'leave a dead.package file, push the changes and '
                        'retire the package in pkgdb.'
        )
        retire_parser.add_argument('reason',
                                   help='Reason for retiring the package')
        retire_parser.set_defaults(command=self.retire)

    # Target functions go here
    def retire(self):
        try:
            module_name = self.cmd.module_name
            ns_module_name = self.cmd.ns_module_name
            namespace = ns_module_name.split(module_name)[0].rstrip('/')
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
            pkgdb = pkgdb2client.PkgDB(
                login_callback=pkgdb2client.ask_password, url="https://admin.rpmfusion.org/pkgdb")
            pkgdb.retire_packages(module_name, branch, namespace=namespace)
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
