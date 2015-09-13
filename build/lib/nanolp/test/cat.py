# Itself testing facilities. Analogue of shell 'cat' command
#
# Author: Balkansoft.BlogSpot.com
# GNU GPL licensed

import sys
from nanolp import core
if len(sys.argv) > 1:
    sys.stdout.write(core.fread23(sys.argv[1]))
