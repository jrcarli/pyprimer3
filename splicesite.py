"""Simple Splice Site Prediction class definition."""

__author__ = "Joe Carli"
__copyright__ = "Copyright 2014"
__credits__ = ["Joe Carli"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Joe Carli"
__email__ = "jrcarli@gmail.com"
__status__ = "Development"

class SpliceSite(object):
    """SpliceSite class definition.

    A SpliceSite (prediction) consists of a start, end, score,
    intron, and exon.
    """
    def __init__(self, start, end, score, intron, exon=''): 
        self.start = start
        self.end = end
        self.score = score
        self.intron = intron
        self.exon = exon

    def getSpliceSite(self):
        """Return a tuple of (position,base,score)"""
        position = self.start + len(self.intron) - 1
        base = self.intron[-1]
        return (position, base, self.score)

    def pprint(self, delim=","):
        """Create a string representation of a SpliceSite.

        A SpliceSite (prediction) string looks like:
        Start<delim>End<delim>Score<delim>Intron<delim>Exon
        """
        #TODO: make sure BOUNDARY is included
        row = ("%d%c"
               "%d%c"
               "%0.2f%c"
               "%s%c"
               "%s"%(
               self.start, delim,
               self.end, delim,
               self.score, delim,
               self.intron, delim,
               self.exon)
             )
        return row

    def __str__(self):
        return self.pprint() 
