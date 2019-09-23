#!/usr/bin/python

import os
import sys

from setuptools import setup, find_packages

try:
    from subprocess import getstatusoutput
except ImportError:
    from commands import getstatusoutput


def bash_completion_dir():
    (sts, output) = getstatusoutput(
        'pkg-config --variable=completionsdir bash-completion')
    return output if not sts and output else '/etc/bash_completion.d'


project_dir = os.path.dirname(os.path.realpath(__file__))
requirements = os.path.join(project_dir, 'requirements.txt')
tests_requirements = os.path.join(project_dir, 'tests-requirements.txt')

with open(requirements, 'r') as f:
    install_requires = [line.strip() for line in f]

with open(tests_requirements, 'r') as f:
    tests_require = [line.strip() for line in f]

ver = sys.version_info
if ver[0] <= 2 and ver[1] < 7:
    tests_require += [
        'unittest2'
    ]
else:
    install_requires += [
        'distro',
    ]


setup(
    name="rfpkg",
    version="1.26.0",
    author="Nicolas Chauvet",
    author_email="kwizart@gmail.com",
    description=("RPM Fusion plugin to rpkg to manage "
                 "package sources in a git repository"),
    license="GPLv2+",
    url="https://github.com/rpmfusion-infra/rfpkg",
    packages=find_packages(),
    data_files=[(bash_completion_dir(), ['conf/bash-completion/rfpkg.bash']),
                ('/etc/rpkg', ['conf/etc/rpkg/rfpkg.conf']),
                ('/usr/share/zsh/site-functions', ['conf/zsh-completion/_rfpkg']),
                ],

    install_requires=install_requires,
    tests_require=tests_require,
    test_suite='nose.collector',

    entry_points={
        'console_scripts': [
            'rfpkg = rfpkg.__main__:main',
        ],
    },

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
