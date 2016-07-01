#!/usr/bin/python
from setuptools import setup

bashcompdir = None
try:
    import subprocess
    bashcompdir = subprocess.check_output(
        ("pkg-config", "--variable=completionsdir", "bash-completion")).strip()
except:
    pass
if not bashcompdir:
    bashcompdir = "/etc/bash_completion.d"

setup(
    name="rfpkg",
    version="1.23.3",
    author="Nicolas Chauvet",
    author_email="kwizart@gmail.com",
    description=("RPM Fusion plugin to rpkg to manage "
                 "package sources in a git repository"),
    license="GPLv2+",
    url="https://github.com/rpmfusion-infra/rfpkg",
    package_dir={'': 'src'},
    packages=['rfpkg'],
    scripts=['src/bin/rfpkg'],
    data_files=[(bashcompdir, ['src/bash-completion/rfpkg']),
                ('/etc/rpkg', ['src/rfpkg.conf', 'src/rfpkg-free.conf', 'src/rfpkg-nonfree.conf']),
                ],
)
