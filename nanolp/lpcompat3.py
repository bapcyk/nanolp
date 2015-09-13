# Compatibility with Python 3.x
#
# Author: Balkansoft.BlogSpot.com
# GNU GPL licensed

from urllib.request import urlopen, Request as UrlRequest
from urllib.parse import urlparse, urlsplit, urlunsplit, quote as urlquote, unquote as urlunquote
import configparser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from html.parser import HTMLParser
import builtins

StringTypes23 = str

def fread23(filename, mode='rt'):
    with open(filename, mode, encoding='utf8') as f:
        return f.read()

def fwrite23(filename, text, mode='wt'):
    with open(filename, mode, encoding='utf8', errors='replace') as f:
        f.write(text)

def bytestostr23(b):
    return str(b, encoding='utf8')

def strtobytes23(s):
    return bytes(s, encoding='utf8')

def reraise23(exc, msg, tb):
    args = [msg] if not exc.args else [msg]+list(exc.args[1:])
    exc.args = args
    raise exc.with_traceback(tb)
    #raise exc(msg).with_traceback(tb)

raw_input23 = input
