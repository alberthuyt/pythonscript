#!/usr/bin/env python
#
# 5/19/15
# 3rd class math
# find number to satisfy following math
# x1 + 13 * x2 / x3 + x4 + 12 * x5 - x6 - 11 + x7 * x8 / x9 - 10 = 66
# x1..x9 have value in [1..9]
from __future__ import division
import itertools


def testsum(x):
    check = x[0] + 13 * x[1] / x[2] + x[3] + 12 * x[4] - x[5] - 11 + x[6] * x[7] / x[8] - 10
    return check

range_number = [i for i in xrange(1,10,1)]
test = list(itertools.permutations(range_number))
print "length list {}".format(len(test))
count = 0

flag = 0 # print 10 solution 
for i in test:
    total = testsum(i)
    if total == 66:
        count += 1
        if flag < 30:
            print "[{},{},{},{},{},{},{},{},{}]".format(i[0],i[1],i[2],i[3],i[4],i[5],i[6],i[7],i[8])
            flag += 1

print "number of solutions {}".format(count)
