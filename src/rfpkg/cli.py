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
        self.register_update()

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

    def register_update(self):
        update_parser = self.subparsers.add_parser(
            'update',
            help='Submit last build as update',
            description='This will create a bodhi update request for the '
                        'current package n-v-r.'
        )
        update_parser.set_defaults(command=self.update)

    # Target functions go here
    def retire(self):
        try:
            # Skip if package is already retired to allow to retire only in
            # pkgdb
            if os.path.isfile(os.path.join(self.cmd.path, 'dead.package')):
                self.log.warn('dead.package found, package probably already '
                              'retired - will not remove files from git or '
                              'overwrite existing dead.package file')
            else:
                self.cmd.retire(self.args.reason)
            self.push()

            # get module name from git, because pyrpkg gets it from SPEC,
            # which is deleted at this point
            cmd = ['git', 'config', '--get', 'remote.origin.url']
            module_name = subprocess.check_output(cmd, cwd=self.cmd.path)
            module_name = \
                module_name.strip().split(self.cmd.gitbaseurl %
                                          {'user': self.cmd.user,
                                           'module': ''})[1]
            branch = self.cmd.branch_merge
            pkgdb = pkgdb2client.PkgDB(
                login_callback=pkgdb2client.ask_password)
            pkgdb.retire_packages(module_name, branch)
        except Exception, e:
            self.log.error('Could not retire package: %s' % e)
            sys.exit(1)

    def _format_update_clog(self, clog):
        ''' Format clog for the update template. '''
        lines = [l for l in clog.split('\n') if l]
        if len(lines) == 0:
            return "- Rebuilt.", ""
        elif len(lines) == 1:
            return lines[0], ""
        log = ["# Changelog:"]
        log.append('# - ' + lines[0])
        for l in lines[1:]:
            log.append('# ' + l)
        log.append('#')
        return lines[0], "\n".join(log)

    def update(self):
        template = """\
[ %(nvr)s ]

# bugfix, security, enhancement, newpackage (required)
type=

# testing, stable
request=testing

# Bug numbers: 1234,9876
bugs=%(bugs)s

%(changelog)s
# Here is where you give an explanation of your update.
notes=%(descr)s

# Enable request automation based on the stable/unstable karma thresholds
autokarma=True
stable_karma=3
unstable_karma=-3

# Automatically close bugs when this marked as stable
close_bugs=True

# Suggest that users restart after update
suggest_reboot=False
"""

        bodhi_args = {'nvr': self.cmd.nvr,
                      'bugs': '',
                      'descr': 'Here is where you give an explanation'
                               ' of your update.'}

        # Extract bug numbers from the latest changelog entry
        self.cmd.clog()
        clog = file('clog').read()
        bugs = re.findall(r'#([0-9]*)', clog)
        if bugs:
            bodhi_args['bugs'] = ','.join(bugs)

        # Use clog as default message
        bodhi_args['descr'], bodhi_args['changelog'] = \
            self._format_update_clog(clog)

        template = textwrap.dedent(template) % bodhi_args

        # Calculate the hash of the unaltered template
        orig_hash = hashlib.new('sha1')
        orig_hash.update(template)
        orig_hash = orig_hash.hexdigest()

        # Write out the template
        out = file('bodhi.template', 'w')
        out.write(template)
        out.close()

        # Open the template in a text editor
        editor = os.getenv('EDITOR', 'vi')
        self.cmd._run_command([editor, 'bodhi.template'], shell=True)

        # Check to see if we got a template written out.  Bail otherwise
        if not os.path.isfile('bodhi.template'):
            self.log.error('No bodhi update details saved!')
            sys.exit(1)
        # If the template was changed, submit it to bodhi
        hash = self.cmd._hash_file('bodhi.template', 'sha1')
        if hash != orig_hash:
            try:
                self.cmd.update('bodhi.template')
            except Exception, e:
                self.log.error('Could not generate update request: %s' % e)
                sys.exit(1)
        else:
            self.log.info('Bodhi update aborted!')

        # Clean up
        os.unlink('bodhi.template')
        os.unlink('clog')

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
