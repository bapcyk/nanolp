# Itself testing facilities. HTTP server
#
# Author: Balkansoft.BlogSpot.com
# GNU GPL licensed

import os
import sys
import getopt
import base64
from nanolp import core

################################################################################

def parse_cmdline():
    """Returns options dictionary, if may continue execution, None otherwise
    (help printing is only need)
    """
    options = {}

    long_opts_with_arg = ['host', 'port', 'login', 'password', 'dir']
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

class TestHTTPServer(core.HTTPServer):
    """HTTP server for tests"""
    def __init__(self, addr=('', 80), handler=None):
        if handler is None: handler = core.SimpleHTTPRequestHandler
        core.HTTPServer.__init__(self, addr, handler)

    @staticmethod
    def __mkauth(login, password):
        auth = "%s:%s"%(login, password)
        try:
            auth = base64.b64encode(auth)
        except TypeError:
            auth = base64.b64encode(auth.encode()).decode()
        return auth

    @staticmethod
    def create_server(host='', port=80, login=None, password=None, dir_=''):
        if not login or not password:
            sys.stdout.write('Run as anonymous!\n')
            handler = None
        else:
            auth = TestHTTPServer.__mkauth(login, password)
            if dir_:
                os.chdir(dir_)
            OPTS = dict(login=login, password=password, auth=auth)
            AuthHTTPHandler.OPTS = OPTS
            handler = AuthHTTPHandler
        return TestHTTPServer(addr=(host, port), handler=handler)

################################################################################

class AuthHTTPHandler(core.SimpleHTTPRequestHandler):
    """Handler of HTTP requests"""
    ## dictionary of options (login, host, port, so on...)
    OPTS = {}

    def __auth(self):
        auth = self.headers.get('Authorization', '')
        if auth != "Basic %s" % self.OPTS['auth']:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="%s"'%self.OPTS['login'])
            self.end_headers();
            return False
        return True

    def do_GET(self):
        if self.__auth(): core.SimpleHTTPRequestHandler.do_GET(self)

################################################################################

def main():
    """Usually is not need, run() is called automatically when do:
      $ python -m unittest discover <SOME DIR>
    Used only for special purpose.
    """
    USAGE = \
'''Simple http server for testing purpose only with basic authorization.
Syntax: [-h] [--host=HOST] [--port=PORT] [--login=LOGIN] [--password=PASSWORD]
[--dir=DIR]
Options:
    -h                   this help
    --host=HOST          bind  to this host name or IP (localhost default)
    --port=PORT          bind to this port number (80 default)
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
    port = int(opts.get('port', 80))
    login = opts.get('login', None)
    password = opts.get('password', None)
    dir_ = opts.get('dir', '')

    httpd = TestHTTPServer.create_server(host=host, port=port, login=login, password=password, dir_=dir_)
    httpd.serve_forever()


if __name__ == '__main__':
    main()
