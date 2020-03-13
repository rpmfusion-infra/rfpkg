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
import platform
import subprocess
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
import koji

from . import cli
from .lookaside import RPMFusionLookasideCache
from pyrpkg.utils import cached_property


class Commands(pyrpkg.Commands):

    def __init__(self, path, lookaside, lookasidehash, lookaside_cgi,
                 gitbaseurl, anongiturl, branchre, kojiprofile,
                 build_client, **kwargs):
        """Init the object and some configuration details."""

        super(Commands, self).__init__(path, lookaside, lookasidehash,
                                       lookaside_cgi, gitbaseurl, anongiturl,
                                       branchre, kojiprofile, build_client,
                                       **kwargs)

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
        self._kojiprofile = None
        self._cert_file = None
        self._ca_cert = None
        # Store this for later
        self._orig_kojiprofile = kojiprofile

        # RPM Fusion default namespace
        self.default_namespace = 'free'
        self.namespace = None
        self.source_entry_type = 'bsd'
        self.hashtype = 'sha512'

    # Add new properties
    @property
    def kojiprofile(self):
        """This property ensures the kojiprofile attribute"""

        if not self._kojiprofile:
            self.load_kojiprofile()
        return self._kojiprofile

    @kojiprofile.setter
    def kojiprofile(self, value):
        self._kojiprofile = value

    def load_kojiprofile(self):
        """This loads the kojiprofile attribute

        This will either use the one passed in via arguments or a
        secondary arch config depending on the package
        """

        # We have to allow this to work, even if we don't have a package
        # we're working on, for things like gitbuildhash.
        try:
            null = self.repo_name
        except:
            self._kojiprofile = self._orig_kojiprofile
            return
        for arch in list(self.secondary_arch.keys()):
            if self.repo_name in self.secondary_arch[arch]:
                self._kojiprofile = arch
                return
        self._kojiprofile = self._orig_kojiprofile

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
            self.dist = 'fc%s' % self._distval
            self.mockconfig = 'fedora-%s-%s-rpmfusion_%s' % (self._distval, self.localarch, self.namespace)
            self.override = 'f%s-%s-override' % (self._distval, self.namespace)
            self._distunset = 'rhel'
        # Works until RHEL 10
        elif re.match(r'el\d$', self.branch_merge) or re.match(r'epel\d$', self.branch_merge):
            self._distval = self.branch_merge.split('el')[1]
            self._distvar = 'rhel'
            self.dist = 'el%s' % self._distval
            self.mockconfig = 'epel-%s-%s-rpmfusion_%s' % (self._distval, self.localarch, self.namespace)
            self.override = 'epel%s-%s-override' % (self._distval, self.namespace)
            self._distunset = 'fedora'
        # master
        elif re.match(r'master$', self.branch_merge):
            self._distval = self._findmasterbranch()
            self._distvar = 'fedora'
            self.dist = 'fc%s' % self._distval
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
                            "--define 'dist .%s'" % self.dist,
                            "--define '%s %s'" % (self._distvar,
                                                  self._distval),
                            "--eval '%%undefine %s'" % self._distunset,
                            "--define '%s 1'" % self.dist]
        if self._runtime_disttag:
            if self.dist != self._runtime_disttag:
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
        if self._package_name_spec in ['buildsys-build-rpmfusion', 'gpac', 'gstreamer1-libav',
            'gstreamer1-plugins-bad-freeworld', 'gstreamer1-plugins-ugly', 'faad2', 'ffmpeg',
            'libde265', 'libdca', 'libmms', 'libquicktime', 'libva-intel-driver', 'mjpegtools',
            'opencore-amr', 'rtmpdump', 'vo-amrwbenc', 'x264', 'x265', 'xvidcore',
            'Cg', 'pcsx2', 'steam', 'xorg-x11-drv-nvidia', 'xorg-x11-drv-nvidia-390xx',
            'xorg-x11-drv-nvidia-340xx'] and self.branch_merge not in ['el6', 'f28',
            'f29', 'f30'] and self.namespace in ['free', 'nonfree']:
            self._target += "-multilibs"

    def load_user(self):
        """This sets the user attribute, based on the RPM Fusion SSL cert."""
        try:
            self._user = rpmfusion_cert.read_user_cert()
        except Exception as e:
            self.log.debug('Could not read RPM Fusion cert, falling back to '
                           'default method: %s' % e)
            super(Commands, self).load_user()

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
        else:
            # We may not have Fedoras.  Find out what rawhide target does.
            try:
                rawhidetarget = self.anon_kojisession.getBuildTarget(
                    'rawhide-free')
            except:
                # We couldn't hit koji, bail.
                raise pyrpkg.rpkgError('Unable to query koji to find rawhide \
                                       target')
            return self._tag2version(rawhidetarget['dest_tag_name'])

    def _determine_runtime_env(self):
        """Need to know what the runtime env is, so we can unset anything
           conflicting
        """

        try:
            mydist = platform.linux_distribution()
        except:
            # This is marked as eventually being deprecated.
            try:
                mydist = platform.dist()
            except:
                runtime_os = 'unknown'
                runtime_version = '0'

        if mydist:
            runtime_os = mydist[0]
            runtime_version = mydist[1]
        else:
            runtime_os = 'unknown'
            runtime_version = '0'

        if runtime_os in ['redhat', 'centos']:
            return 'el%s' % runtime_version
        if runtime_os == 'Fedora':
            return 'fc%s' % runtime_version

        # fall through, return None
        return None

    def construct_build_url(self):
        """Override build URL for RPM Fusion Koji build

        In RPM Fusion Koji, anonymous URL should have prefix "git+https://"
        """
        url = super(Commands, self).construct_build_url()
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

    def update(self, template='bodhi.template', bugs=[]):
        """Submit an update to bodhi using the provided template."""

        # build up the bodhi arguments, based on which version of bodhi is
        # installed
        bodhi_major_version = _get_bodhi_version()[0]
        if bodhi_major_version < 2:
            cmd = ['bodhi', '--new', '--release', self.branch_merge,
                   '--file', 'bodhi.template', self.nvr, '--username',
                   self.user]
        elif bodhi_major_version == 2:
            cmd = ['bodhi', 'updates', 'new', '--file', 'bodhi.template',
                   '--user', self.user, self.nvr]
        else:
            msg = 'This system has bodhi v{0}, which is unsupported.'
            msg = msg.format(bodhi_major_version)
            raise Exception(msg)
        self._run_command(cmd, shell=True)

    def load_kojisession(self, anon=False):
        """Initiate a koji session.

        The koji session can be logged in or anonymous
        """
        koji_config = self.read_koji_config()

        # Expand out the directory options
        for name in ('cert', 'ca', 'serverca'):
            path = koji_config[name]
            if path:
                koji_config[name] = os.path.expanduser(path)

        # save the weburl and topurl for later use as well
        self._kojiweburl = koji_config['weburl']
        self._topurl = koji_config['topurl']

        self.log.debug('Initiating a %s session to %s',
                       os.path.basename(self.build_client), koji_config['server'])

        # Build session options used to create instance of ClientSession
        session_opts = koji.grab_session_options(koji_config)

        try:
            session = koji.ClientSession(koji_config['server'], session_opts)
        except Exception:
            raise rpkgError('Could not initiate %s session' % os.path.basename(self.build_client))
        else:
            if anon:
                self._anon_kojisession = session
            else:
                self._kojisession = session

        if not anon:
            try:
                self.login_koji_session(koji_config, self._kojisession)
            except pyrpkg.rpkgAuthError:
                self.log.info("You might want to run rpmfusion-cert -n to "
                              "regenerate SSL certificate. For more info see "
                              "https://rpmfusion.org/Contributors#If_SSL_certificate_expired")
                raise


def _get_bodhi_version():
    """
    Use bodhi --version to determine the version of the Bodhi CLI that's
    installed on the system, then return a list of the version components.
    For example, if bodhi --version returns "2.1.9", this function will return
    [2, 1, 9].
    """
    bodhi = subprocess.Popen(['bodhi', '--version'], stdout=subprocess.PIPE)
    version = bodhi.communicate()[0].strip()
    return [int(component) for component in version.split('.')]


if __name__ == "__main__":
    from rfpkg.__main__ import main
    main()
