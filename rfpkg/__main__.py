# rfpkg - a script to interact with the RPM Fusion Packaging system
#
# Copyright (C) 2011 Red Hat Inc.
# Author(s): Jesse Keating <jkeating@redhat.com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
# the full text of the license.

# PYTHON_ARGCOMPLETE_OK

import logging
import os
import sys

import six

import rfpkg
import pyrpkg
import pyrpkg.utils

import argparse

if six.PY3:  # SafeConfigParser == ConfigParser, former deprecated in >= 3.2
    from six.moves.configparser import ConfigParser
else:
    from six.moves.configparser import SafeConfigParser as ConfigParser


cli_name = os.path.basename(sys.argv[0])


def main():
    default_user_config_path = os.path.join(
        os.path.expanduser('~'), '.config', 'rpkg', '%s.conf' % cli_name)
    # Setup an argparser and parse the known commands to get the config file
    # - use the custom ArgumentParser class from pyrpkg.cli and disable
    #   argument abbreviation to ensure that --user will be not treated as
    #   --user-config
    parser = pyrpkg.cli.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument('-C', '--config', help='Specify a config file to use',
                        default='/etc/rpkg/%s.conf' % cli_name)
    parser.add_argument(
        '--user-config', help='Specify a user config file to use',
        default=default_user_config_path)

    (args, other) = parser.parse_known_args()

    # Make sure we have a sane config file
    if not os.path.exists(args.config) and \
       not other[-1] in ['--help', '-h', 'help']:
        sys.stderr.write('Invalid config file %s\n' % args.config)
        sys.exit(1)

    # Setup a configuration object and read config file data
    config = ConfigParser()
    config.read(args.config)
    config.read(args.user_config)

    client = rfpkg.cli.rfpkgClient(config, name=cli_name)
    client.do_imports(site='rfpkg')
    client.parse_cmdline()

    if not client.args.path:
        try:
            client.args.path = pyrpkg.utils.getcwd()
        except Exception:
            print('Could not get current path, have you deleted it?')
            sys.exit(1)

    # setup the logger -- This logger will take things of INFO or DEBUG and
    # log it to stdout.  Anything above that (WARN, ERROR, CRITICAL) will go
    # to stderr.  Normal operation will show anything INFO and above.
    # Quiet hides INFO, while Verbose exposes DEBUG.  In all cases WARN or
    # higher are exposed (via stderr).
    log = pyrpkg.log
    client.setupLogging(log)

    if client.args.v:
        log.setLevel(logging.DEBUG)
    elif client.args.q:
        log.setLevel(logging.WARNING)
    else:
        log.setLevel(logging.INFO)

    # Run the necessary command
    try:
        sys.exit(client.args.command())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        log.error('Could not execute %s: %s' %
                  (client.args.command.__name__, e))
        if client.args.v:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
