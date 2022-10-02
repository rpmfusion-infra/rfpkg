# -*- coding: utf-8 -*-
# completers.py - custom argument completers module for rfpkg
#
# Copyright (C) 2019 Red Hat Inc.
# Author(s): Ondrej Nosek <onosek@redhat.com>,
#            Dominik Rumian <drumian@redhat.com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
# the full text of the license.

import subprocess
import sys

from argcomplete.completers import ChoicesCompleter


def distgit_branches(**kwargs):
    format = "--format=\"%(refname:short)\""
    # TODO: Somehow get $path from argument-string
    remotes = subprocess.check_output(
        "git for-each-ref %s 'refs/remotes' | sed 's,.*/,,'" % format,
        shell=True).decode(sys.stdout.encoding).split()
    heads = subprocess.check_output(
        " git for-each-ref %s 'refs/heads'" % format,
        shell=True).decode(sys.stdout.encoding).split()
    return remotes + heads


def rfpkg_packages(prefix, **kwargs):
    if len(prefix):
        return subprocess.check_output(
            "repoquery -C --qf=%{{sourcerpm}} \"{}*\" 2>/dev/null | sed -r "
            "'s/(-[^-]*){{2}}\\.src\\.rpm$//'"
            .format(prefix), shell=True).decode(sys.stdout.encoding).split()
    else:
        return []


def list_targets(**kwargs):
    return tuple(subprocess.check_output("koji list-targets --quiet 2>/dev/null | cut -d\" \" -f1",
                                         shell=True).decode(sys.stdout.encoding).split())


build_arches = ChoicesCompleter(("i386", "i686", "x86_64", "armv5tel",
                                 "armv7hl", "armv7hnl", "ppc", "ppc64",
                                 "ppc64le", "ppc64p7", "s390", "s390x"))
