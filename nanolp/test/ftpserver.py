# Itself testing facilities. FTP server (based on pyftpdlib)
#
# Author: Balkansoft.BlogSpot.com
# GNU GPL licensed

import os
import sys
import getopt
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

################################################################################

def parse_cmdline():
    """Returns options dictionary, if may continue execution, None otherwise
    (help printing is only need)
    """
    options = {}

    long_opts_with_arg = ['host', "port", "login", "password", "dir"]
    long_opts = ['%s='%o for o in long_opts_with_arg]

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'h', long_opts)
    except getopt.GetoptError as x:
        sys.stderr.write('Syntax error! See help (-h)\n')
        sys.exit(1)

    _UsageAndExit = False
    for o, v in opts:
        if o == '-h':
            _UsageAndExit = True
        elif o == '-q':
            options['q'] = True
        elif o in ('--%s'%o for o in long_opts_with_arg):
            options[o.lstrip('-')] = v

    if _UsageAndExit:
        return None
    else:
        return options

################################################################################

def main():
    """Usually is not need, run() is called automatically when do:
      $ python -m unittest discover <SOME DIR>
    Used only for special purpose.
    """
    USAGE = \
'''Simple ftp server for testing purpose only.
Syntax: [-h] [--host=HOST] [--port=PORT] [--login=LOGIN] [--password=PASSWORD]
[--dir=DIR]
Options:
    -h                   this help
    --host=HOST          bind  to this host name or IP (localhost default)
    --port=PORT          bind to this port number (21 default)
    --login=LOGIN        user name to login (anonymous default)
    --password=PASSWORD  user password
    --dir=DIR            browse directory (current dir default)
'''
    opts = parse_cmdline()
    if opts is None:
        sys.stdout.write(USAGE)
        sys.exit(0)
    # processing other options
    host = opts.get('host', '')
    port = int(opts.get('port', 21))
    login = opts.get('login', None)
    password = opts.get('password', None)
    dir_ = opts.get('dir', os.getcwd())

    ftp_handler = FTPHandler
    authorizer = DummyAuthorizer()
    ftp_handler.authorizer = authorizer
    if login and password:
        # Define a new user having full r/w permissions
        authorizer.add_user(login, password, dir_, perm='elradfmw')
    else:
        sys.stdout.write('Run as anonymous!\n')
        authorizer.add_anonymous(dir_)

    # Define a customized banner (string returned when client connects)
    ftp_handler.banner = "Test FTP server"
    address = (host, port)
    ftpd = FTPServer(address, ftp_handler)
    # set a limit for connections
    ftpd.max_cons = 256
    ftpd.max_cons_per_ip = 256
    # start ftp server
    ftpd.serve_forever()

if __name__ == '__main__':
    main()
