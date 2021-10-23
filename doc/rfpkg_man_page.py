# Print a man page from the help texts.


import os
import sys

from six.moves.configparser import ConfigParser


if __name__ == '__main__':
    module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, module_path)

    config = ConfigParser()
    config.read(
        os.path.join(module_path, 'conf', 'etc', 'rpkg', 'rfpkg.conf'))

    import pyrpkg.man_gen
    try:
        import rfpkg
    except ImportError:
        sys.path.append('src/')
        import rfpkg
    client = rfpkg.cli.rfpkgClient(config=config, name='rfpkg')
    pyrpkg.man_gen.generate(client.parser,
                            client.subparsers,
                            identity='rfpkg',
                            sourceurl='https://github.com/rpmfusion-infra/rfpkg')
