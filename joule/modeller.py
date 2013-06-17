#!/usr/bin/env python
#
# Copyright (c) 2013, Roberto Riggio
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the CREATE-NET nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY CREATE-NET ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL CREATE-NET BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
A command line utility for interfacing with the energino power 
consumption monitor.
"""

import os
import json
import optparse
import logging 
import sqlite3
import numpy as np
from scipy.optimize import curve_fit

LOG_FORMAT = '%(asctime)-15s %(message)s'
DEFAULT_JOULE = '~/joule.json'

def compute_models(data):

    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    c.execute('''create table data (src, dst, bitrate_mbps, packetsize_bytes, losses, median, mean)''')
    conn.commit()

    for stint in data['stints']:
        row = [ stint['src'], stint['dst'], stint['bitrate_mbps'], stint['packetsize_bytes'], stint['stats']['losses'], stint['stats']['median'], stint['stats']['mean']]
        c.execute("""insert into data values (?,?,?,?,?,?,?)""", row)
        conn.commit()

    for model in data['models'].values():

        groups = []
        c.execute("select %s from data group by %s" % (model['group_by'], model['group_by']))
        for row in c:
            groups.append(row[0])
            
        model['groups'] = {}
        for group in groups:
            model['groups'][group] = { 'points' : [], 'params' : None }
            c.execute("select %s, median from data where src = \"%s\" and dst = \"%s\" and %s = %s" % (model['select'], model['src'], model['dst'], model['group_by'], group))
            for row in c:
                model['groups'][group]['points'].append(row)
            A = np.array(model['groups'][group]['points'])
            popt, _ = curve_fit(eval(model['lambda']), A[:,0], A[:,1])
            model['groups'][group]['params'] = list(popt)

def main():

    p = optparse.OptionParser()
    p.add_option('--joule', '-j', dest="joule", default=DEFAULT_JOULE)
    p.add_option('--verbose', '-v', action="store_true", dest="verbose", default=False)    
    p.add_option('--log', '-l', dest="log")
    options, _ = p.parse_args()

    with open(os.path.expanduser(options.joule)) as data_file:    
        data = json.load(data_file)

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, filename=options.log, filemode='w')
    else:
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, filename=options.log, filemode='w')
   
    compute_models(data)

    with open(os.path.expanduser(options.joule), 'w') as data_file:    
        json.dump(data, data_file, sort_keys=True, indent=4, separators=(',', ': '))

if __name__ == "__main__":
    main()