#!/usr/bin/env python

from tests import getSequence
from splicesite import SpliceSite
import fruitfly

s = getSequence()
spliceSites = fruitfly.getSpliceSitePredictions(s)

for ss in spliceSites:
    print ss
