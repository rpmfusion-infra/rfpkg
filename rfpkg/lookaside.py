# Copyright (c) 2015 - Red Hat Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
# the full text of the license.


"""Interact with the RPM Fusion lookaside cache

We need to override the pyrpkg.lookasidecache module to handle our custom
download path.
"""


import os
from pyrpkg.lookaside import CGILookasideCache


class RPMFusionLookasideCache(CGILookasideCache):
    def __init__(self, hashtype, download_url, upload_url,
                 client_cert, ca_cert, namespace):
        super(RPMFusionLookasideCache, self).__init__(
            hashtype, download_url, upload_url, client_cert=client_cert,
            ca_cert=ca_cert)

        self.download_path_md5 = (
            namespace + '/%(name)s/%(filename)s/%(hash)s/%(filename)s')
        self.download_path = (
            namespace + '/%(name)s/%(filename)s/%(hashtype)s/%(hash)s/%(filename)s')

    def get_download_url(self, name, filename, hash, hashtype=None, **kwargs):
        path_dict = {'name': name, 'filename': filename,
                     'hash': hash, 'hashtype': hashtype}
        path_dict.update(kwargs)
        if hashtype == 'md5':
            path = self.download_path_md5 % path_dict
        else:
            path = self.download_path % path_dict
        return os.path.join(self.download_url, path)

