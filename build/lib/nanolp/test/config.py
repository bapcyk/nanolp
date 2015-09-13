# Configuration parameters of testing. User can change them here, they has
# effects anywhere (and in tests files too). If some tests failed, these
# parameters may helps.
#
# NOTE EACH PARAM SHOULD ENDS WITH '_PARAM' AND BE IN UPPER-CASE!
#
# Author: Balkansoft.BlogSpot.com
# GNU GPL licensed

from nanolp.core import TCP_PORT

## PORT may be number of pair (of 1 or 2 items) - random from range
## START_TIME is time need to server to start up (in seconds)
HTTP_HOST_PARAM = 'localhost'
HTTP_PORT_PARAM = TCP_PORT([8000])
HTTP_LOGIN_PARAM = 'tester'
HTTP_PASSWORD_PARAM = 123
HTTP_START_TIME_PARAM = 1
FTP_HOST_PARAM = 'localhost'
FTP_PORT_PARAM = TCP_PORT([8021])
FTP_LOGIN_PARAM = 'tester'
FTP_PASSWORD_PARAM = 123
FTP_START_TIME_PARAM = 1
