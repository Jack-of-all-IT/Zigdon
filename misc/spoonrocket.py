#!/usr/bin/python

""" Monitor spoonrocket item availability. Will loop over the site's data feed
until it finds the item is not sold out. Will exit with a status of 0 on
success, 1 if there was an error. 

The exit code allows to use this in a pipeline. Say, on OSX:

$ gem install terminal-notifier
$ ./spoonrocket.py -v && terminal-notifier -title 'Spoonrocket exists!' \
-message "GO GO GO" -open http://www.spoonrocket.com

"""

import sys
import httplib2
import json
import time

from optparse import OptionParser

parser = OptionParser()

parser.add_option("-s", "--sleep", dest="sleep", default=5,
                  help="Seconds to wait between polls")
parser.add_option("-u", "--url", dest="url",
                  default="http://api.spoonrocket.com/userapi//menu?zone_id=8",
                  help="Spoonrocket URL to poll")
parser.add_option("-v", "--vegetarian", action="store_true",
                  dest="vegetarian", default=True)
parser.add_option("-m", "--meat", action="store_false", dest="vegetarian")

(options, args) = parser.parse_args()

h = httplib2.Http(disable_ssl_certificate_validation=True)
while True:
    resp, data = h.request(options.url)

    if resp['status'] != '200':
        print "Failed to poll spoonrocket, request returned:\n%r" % resp
        sys.exit(1)

    try:
        j = json.loads(data)
    except ValueError, e:
        print "Failed to parse json: %s" % E
        sys.exit(1)

    info = None
    for i in j['menu']:
        if options.vegetarian and 'vegetarian' in i['properties']:
            info = i
            break
        if not options.vegetarian and not 'vegetarian' in i['properties']:
            info = i
            break

    status = info['sold_out_temporarily'] and 'sold out' or str(info['qty'])
    print "%s: %s" % (info['name'], status)

    if status != 'sold out':
        sys.exit(0)

    time.sleep(options.sleep)

