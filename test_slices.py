#! /usr/bin/python

# Copyright (c) 2015, Matthew P. Grosvenor
# All rights reserved. See LICENSE for more details

import sys
import redo

hosts = ["test%i" % x for x in range(0,15)]

redo = redo.Redo(hosts)


tests_index = [-1,1,"test7"]
results = ["['test14']", "['test1']", "['test7']"]

i = 1
for i in range(0,len(results)):
    test = tests_index[i]
    result = str(redo[test])
    expect = results[i]
    if not expect == result:
        print "TEST %i: Failure: expected %s but got %s" % (i,result,expect)
    else:
        print "TEST %i: Success" % i

tests_slice = [ slice(-7,None, None),        \
                slice(3,sys.maxint,None),    \
                slice("test1","test7",None), \
                slice("test1",None,None),    \
                slice(None,"test7",None)     ]
               

def make_result(start,stop):
    return "[" + ", ".join(["'test%i'" % i for i in range(start,stop)]) + "]"
    
results = [ make_result(8,15), \
            make_result(3,15), \
            make_result(1,8),  \
            make_result(1,15), \
            make_result(0,8),  \
          ]

for i in range(0,len(results)):
    test = tests_slice[i]
    result = str(redo[test])
    expect = results[i]
    if not expect == result:        
        print "TEST %i: Failure: expected %s but got %s" % (i + len(tests_index),result,expect)
    else:
        print "TEST %i: Success" % (i + len(tests_index))

