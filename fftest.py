#!/usr/bin/env python

from splicesite import SpliceSite
import fruitfly

with open('sequence.txt','rb') as f:
    a = f.read()

with open('variant.txt','rb') as f:
    b = f.read()

sitesA = fruitfly.getSpliceSitePredictions(a)
sitesB = fruitfly.getSpliceSitePredictions(b)

print "~"*10 + " Expected " + "~"*10
for ss in sitesA:
    print ss

print ""
print "~"*10 + " Variant " + "~"*10
for ss in sitesB:
    print ss

print ""
print "~"*10 + " Comparing Results " + "~"*10
print ""

# List where we will store the SpliceSites to print
# These are the sites that are "interesting"
printList = []

for i, sb in enumerate(sitesB):
    (posB,baseB,scoreB) = sb.getSpliceSite()
    foundMatch = False
    for j, sa in enumerate(sitesA):
        (posA,baseA,scoreA) = sa.getSpliceSite()
        if posA==posB:
            foundMatch = True
            if scoreA==scoreB:
                if baseA != baseB:
                    print("Base changed from %s to %s at position %d "
                        "with score %0.2f"%(baseA, baseB, posA, scoreA))
            else:
                delta = abs(scoreA - scoreB)
                if delta >= 0.4:
                    print("Score changed by %0.2f from %0.2f to %0.2f "
                        "at position %d."%(delta, scoreA, scoreB, posA))
    if not foundMatch:

        if posB >= len(a):
            print("Oops! Somehow the length of our expected and varied "
                "sequences is not equivalent (%d for expected, "
                "%d for varied)."%(len(a),len(b)))
            break
        origBase = a[posB].lower()

        print("New splice site predicted at position %d with score %0.2f.\n"
            "Original base was '%s' and new base is '%s'."
            %(posB, scoreB, origBase, baseB))

        printList.append(sb)
print ""

if len(printList) > 0:
    print "Start\tEnd\tScore\tIntron\t\t\tExon"
    for ss in printList:
        print ss.pprint(delim='\t')
print ""
