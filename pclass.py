"""
Primer class
TODO: DOCUMENT
"""

__author__ = "Joe Carli"
__copyright__ = "Copyright 2014"
__credits__ = ["Joe Carli"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Joe Carli"
__email__ = "jrcarli@gmail.com"
__status__ = "Development"

class Primer(object):
    def __init__(self,chrom,pos,fSeq,rSeq,size):
        self.chrom = chrom
        self.pos = pos
        self.fSeq = fSeq
        self.rSeq = rSeq
        self.size = size

    def __str__(self,delim=','):
        """Doesn't make sense to always tab-delim"""
        #print "Inside Primer str func"
        rowA = "%s: %dF%c%s%c%d"%(self.chrom,self.pos,
            delim,self.fSeq,delim,self.size)
        rowB = "%s: %dR%c%s"%(self.chrom,self.pos,delim,self.rSeq)
        return (rowA + "\n" + rowB)
