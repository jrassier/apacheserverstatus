from apacheserverstatus import ApacheServerStatus
from pprint import pprint

status = ApacheServerStatus('http://somebox.somewhere.edu:8008/server-status')
status.dump()
