# Compatibility with Python 2.7.x
#
# Author: Balkansoft.BlogSpot.com
# GNU GPL licensed

from urllib2 import urlopen, Request as UrlRequest
from urlparse import urlparse, urlsplit, urlunsplit
from urllib import quote as urlquote, unquote as urlunquote
import ConfigParser as configparser
from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer
from HTMLParser import HTMLParser
import __builtin__ as builtins

StringTypes23 = (str, unicode)

# XXX Usage of codecs.open() causes errors in re-expr, so fread23() is implemented
def fread23(filename, mode='rt'):
    with open(filename, mode) as f:
        return f.read().decode('utf8')

def fwrite23(filename, text, mode='wt'):
    with open(filename, mode) as f:
        f.write(text.encode('utf8', errors='replace'))

def bytestostr23(b):
    return str(b)

def strtobytes23(s):
    return bytes(s)

def reraise23(exc, msg, tb):
    # FIXME tb ignore, bcz some excpetions has more posit. args then its .args attr
    # it's kept (?), see http://blog.ianbicking.org/2007/09/12/re-raising-exceptions/
    args = [msg] if not exc.args else [msg]+list(exc.args[1:])
    exc.args = args
    raise

raw_input23 = raw_input
