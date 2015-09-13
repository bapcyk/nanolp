# Itself testing facilities
#
# Author: Balkansoft.BlogSpot.com
# GNU GPL licensed

import site
import glob
import sys
import os
from nanolp import _instlog

# usually 'site-packages' or '/usr/local/lib/pythonXX/..' or other
testdir = os.path.join(_instlog.PURELIB_DIR, 'nanolp', 'test')
if not os.path.exists(testdir):
    raise ImportError("Can not find directory of 'nanolp.test' package")

# add nanolp/test/*.zip as places of additional modules
zips = glob.glob(os.path.join(testdir, '*.zip'))
for zf in zips:
    # add all zip files to be source of imported modules
    sys.path.insert(0, zf)
