# rfpkg - a Python library for RPM Packagers
#
# Copyright (C) 2011 Red Hat Inc.
# Author(s): Jesse Keating <jkeating@redhat.com>
# Copyright (C) 2016 - Nicolas Chauvet <kwizart@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
# the full text of the license.

import pyrpkg
import os
import git
import re

import rpmfusion_cert
from six.moves.urllib_parse import urlparse

from . import cli
from .lookaside import RPMFusionLookasideCache
from pyrpkg.utils import cached_property


class Commands(pyrpkg.Commands):

    def __init__(self, *args, **kwargs):
        """Init the object and some configuration details."""

        super(Commands, self).__init__(*args, **kwargs)

        # New data
        self.secondary_arch = {
            'ppc': [
                'apmud',
                'libbsr',
                'librtas',
                'libservicelog',
                'libvpd',
                'lsvpd',
                'powerpc-utils',
                'powerpc-utils-papr',
                'powerpc-utils-python',
                'ppc64-diag',
                'ppc64-utils',
                'servicelog',
                'yaboot',
            ], 'arm': ['xorg-x11-drv-omapfb'],
               's390': ['s390utils', 'openssl-ibmca', 'libica', 'libzfcphbaapi']
        }

        # New properties
        self._cert_file = None
        self._ca_cert = None

        # RPM Fusion default namespace
        self.default_namespace = 'free'
        self.namespace = None
        self.source_entry_type = 'bsd'
        self.hashtype = 'sha512'

    # Add new properties
    def load_user(self):
        """This sets the user attribute, based on the RPM Fusion SSL cert."""
        try:
            self._user = rpmfusion_cert.read_user_cert()
        except Exception as e:
            self.log.debug('Could not read RPM Fusion cert, falling back to '
                           'default method: %s' % e)
            super(Commands, self).load_user()

    @cached_property
    def cert_file(self):
        """A client-side certificate for SSL authentication

        We override this from pyrpkg because we actually need a client-side
        certificate.
        """
        return os.path.expanduser('~/.rpmfusion.cert')

    @cached_property
    def ca_cert(self):
        """A CA certificate to authenticate the server in SSL connections

        We override this from pyrpkg because we actually need a custom
        CA certificate.
        """
        return os.path.expanduser('~/.rpmfusion-server-ca.cert')

    def load_ns_repo_name(self):
        """Loads a RPM Fusion package repository."""

        if self.push_url:
            parts = urlparse(self.push_url)

            if self.distgit_namespaced:
                path_parts = [p for p in parts.path.split("/") if p]
                ns_repo_name = "/".join(path_parts[-2:])
                _ns = path_parts[-2]

            if ns_repo_name.endswith('.git'):
                ns_repo_name = ns_repo_name[:-len('.git')]
            self._ns_repo_name = ns_repo_name
            self.namespace = _ns
            return

    @cached_property
    def lookasidecache(self):
        """A helper to interact with the lookaside cache

        We override this because we need a different download path.
        """
        self.load_ns_repo_name()
        self._cert_file = os.path.expanduser('~/.rpmfusion.cert')

        return RPMFusionLookasideCache(
            self.lookasidehash, self.lookaside, self.lookaside_cgi,
            client_cert=self._cert_file, ca_cert=self._ca_cert, namespace=self.namespace)

    # Overloaded property loaders
    def load_rpmdefines(self):
        """Populate rpmdefines based on branch data"""

        # Determine runtime environment
        self._runtime_disttag = self._determine_runtime_env()
        self.load_ns_repo_name()

        # We only match the top level branch name exactly.
        # Anything else is too dangerous and --release should be used
        # This regex works until after Fedora 99.
        if re.match(r'f\d\d$', self.branch_merge):
            self._distval = self.branch_merge.split('f')[1]
            self._distvar = 'fedora'
            self._disttag = 'fc%s' % self._distval
            self.mockconfig = 'fedora-%s-%s-rpmfusion_%s' % (self._distval, self.localarch, self.namespace)
            self.override = 'f%s-%s-override' % (self._distval, self.namespace)
            self._distunset = 'rhel'
        # Works until RHEL 10
        elif re.match(r'el\d$', self.branch_merge) or \
            re.match(r'epel\d$', self.branch_merge):
            self._distval = self.branch_merge.split('el')[1]
            self._distvar = 'rhel'
            self._disttag = 'el%s' % self._distval
            self.mockconfig = 'epel-%s-%s-rpmfusion_%s' % (self._distval, self.localarch, self.namespace)
            self.override = 'epel%s-%s-override' % (self._distval, self.namespace)
            self._distunset = 'fedora'
        # master
        elif re.match(r'master$', self.branch_merge):
            self._distval = self._findmasterbranch()
            self._distvar = 'fedora'
            self._disttag = 'fc%s' % self._distval
            self.mockconfig = 'fedora-rawhide-%s-rpmfusion_%s' % (self.localarch, self.namespace)
            self.override = None
            self._distunset = 'rhel'
        # If we don't match one of the above, punt
        else:
            raise pyrpkg.rpkgError('Could not find the release/dist from branch name '
                                   '%s\nPlease specify with --release' %
                                   self.branch_merge)
        self._rpmdefines = ["--define '_sourcedir %s'" % self.path,
                            "--define '_specdir %s'" % self.path,
                            "--define '_builddir %s'" % self.path,
                            "--define '_srcrpmdir %s'" % self.path,
                            "--define '_rpmdir %s'" % self.path,
                            "--define 'dist .%s'" % self._disttag,
                            "--define '%s %s'" % (self._distvar,
                                                  self._distval),
                            "--eval '%%undefine %s'" % self._distunset,
                            "--define '%s 1'" % self._disttag]
        if self._runtime_disttag:
            if self._disttag != self._runtime_disttag:
                # This means that the runtime is known, and is different from
                # the target, so we need to unset the _runtime_disttag
                self._rpmdefines.append("--eval '%%undefine %s'" %
                                        self._runtime_disttag)

    def load_target(self):
        """This creates the target attribute based on branch merge"""

        self.load_ns_repo_name()
        self.load_nameverrel()
        if self.branch_merge == 'master':
            self._target = 'rawhide-%s' % self.namespace
        else:
            self._target = '%s-%s' % ( self.branch_merge , self.namespace)
        if self._package_name_spec in ['buildsys-build-rpmfusion', 'gstreamer1-libav',
            'gstreamer1-plugins-bad-freeworld', 'gstreamer1-plugins-ugly', 'faad2', 'ffmpeg',
            'libde265', 'libdca', 'libmms', 'libquicktime', 'libva-intel-driver', 'mjpegtools',
            'opencore-amr', 'rtmpdump', 'vo-amrwbenc', 'x264', 'x265', 'xvidcore', 'zsnes',
            'Cg', 'dega-sdl', 'gens', 'pcsx2', 'steam', 'xorg-x11-drv-nvidia',
            'xorg-x11-drv-nvidia-470xx', 'xorg-x11-drv-nvidia-390xx',
            'xorg-x11-drv-nvidia-340xx', 'unace'] and self.branch_merge not in ['el6', 'f28',
            'f29', 'f30'] and self.namespace in ['free', 'nonfree']:
            self._target += "-multilibs"

    def _tag2version(self, dest_tag):
        """ get the '26' part of 'f26-foo' string """
        return dest_tag.split('-')[0].replace('f', '')

    # New functionality
    def _findmasterbranch(self):
        """Find the right "rpmfusion" for master"""

        # If we already have a koji session, just get data from the source
        if self._kojisession:
            rawhidetarget = self.kojisession.getBuildTarget('rawhide-free')
            return self._tag2version(rawhidetarget['dest_tag_name'])

        # We may not have Fedoras.  Find out what rawhide target does.
        try:
            rawhidetarget = self.anon_kojisession.getBuildTarget('rawhide-free')
        except:
            # We couldn't hit Koji. Continue, because rfpkg may work offline.
            self.log.debug('Unable to query Koji to find rawhide target. Continue offline.')
        else:
            return self._tag2version(rawhidetarget['dest_tag_name'])

        # Create a list of "fedoras"
        fedoras = []

        # Create a regex to find branches that exactly match f##.  Should not
        # catch branches such as f14-foobar
        branchre = r'f\d\d$'

        # Find the repo refs
        for ref in self.repo.refs:
            # Only find the remote refs
            if type(ref) == git.RemoteReference:
                # Search for branch name by splitting off the remote
                # part of the ref name and returning the rest.  This may
                # fail if somebody names a remote with / in the name...
                if re.match(branchre, ref.name.split('/', 1)[1]):
                    # Add just the simple f## part to the list
                    fedoras.append(ref.name.split('/')[1])
        if fedoras:
            # Sort the list
            fedoras.sort()
            # Start with the last item, strip the f, add 1, return it.
            return(int(fedoras[-1].strip('f')) + 1)
        else:
            raise pyrpkg.rpkgError('Unable to find rawhide target')

    def _determine_runtime_env(self):
        """Need to know what the runtime env is, so we can unset anything
           conflicting
        """
        try:
            runtime_os, runtime_version, _ = linux_distribution()
        except Exception:
            return None

        if runtime_os in ['redhat', 'centos']:
            return 'el%s' % runtime_version
        if runtime_os == 'Fedora':
            return 'fc%s' % runtime_version
        if (runtime_os == 'Red Hat Enterprise Linux Server' or
                runtime_os.startswith('CentOS')):
            return 'el{0}'.format(runtime_version.split('.')[0])

        # fall through, return None
        return None

    def construct_build_url(self, *args, **kwargs):
        """Override build URL for RPM Fusion Koji build

        In RPM Fusion Koji, anonymous URL should have prefix "git+https://"
        """
        url = super(Commands, self).construct_build_url(*args, **kwargs)
        if not url.startswith('git'):
            url = 'git+{0}'.format(url)
        return url

    def retire(self, message):
        """Delete all tracked files and commit a new dead.package file

        Use optional message in commit.

        Runs the commands and returns nothing
        """
        cmd = ['git']
        if self.quiet:
            cmd.append('--quiet')
        cmd.extend(['rm', '-rf', '.'])
        self._run_command(cmd, cwd=self.path)

        fd = open(os.path.join(self.path, 'dead.package'), 'w')
        fd.write(message + '\n')
        fd.close()

        cmd = ['git', 'add', os.path.join(self.path, 'dead.package')]
        self._run_command(cmd, cwd=self.path)

        self.commit(message=message)

    def load_kojisession(self, anon=False):
        try:
            return super(Commands, self).load_kojisession(anon)
        except pyrpkg.rpkgAuthError:
            self.log.info("You might want to run rpmfusion-packager-setup "
                          "or rpmfusion-cert -n to regenerate SSL certificate. "
                          "For more info see https://rpmfusion.org/Contributors"
                          "#If_SSL_certificate_expired")
            raise


if __name__ == "__main__":
    from rfpkg.__main__ import main
    main()
