#!/usr/bin/python
from setuptools import setup
try:
    from subprocess import getstatusoutput
except:
    from commands import getstatusoutput


def bash_completion_dir():
    (sts, output) = getstatusoutput(
        'pkg-config --variable=completionsdir bash-completion')
    return output if not sts and output else '/etc/bash_completion.d'

setup(
    name="rfpkg",
    version="1.25.5",
    author="Nicolas Chauvet",
    author_email="kwizart@gmail.com",
    description=("RPM Fusion plugin to rpkg to manage "
                 "package sources in a git repository"),
    license="GPLv2+",
    url="https://github.com/rpmfusion-infra/rfpkg",
    package_dir={'': 'src'},
    packages=['rfpkg'],
    scripts=['src/bin/rfpkg'],
    data_files=[(bash_completion_dir(), ['src/rfpkg.bash']),
                ('/etc/rpkg', ['src/rfpkg.conf']),
                ('/usr/share/zsh/site-functions', ['src/_rfpkg']),
                ],
)
