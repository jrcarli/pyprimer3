"""Simple Primer class definition."""

__author__ = "Joe Carli"
__copyright__ = "Copyright 2014"
__credits__ = ["Joe Carli"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Joe Carli"
__email__ = "jrcarli@gmail.com"
__status__ = "Development"

class Primer(object):
    """Primer class definition.

    A Primer consists of a chromsome identifier (integer or X or Y),
    a position within the chromosome, the forward and reverse sequences,
    and the length of a primer (number of bases).

    Primer3 returns the forward and reverse sequences and the primer length.
    The chromosome and position are inputs for Primer3.
    """
    def __init__(self, chrom, pos, fSeq, rSeq, size):
        self.chrom = chrom
        self.pos = pos
        self.fSeq = fSeq
        self.rSeq = rSeq
        self.size = size

    def __str__(self, delim=','):
        """Create a string representation of a Primer.

        A Primer string looks like:
        <chromosome>: <position>F<delim><fseq><delim><size>
        <chromosome>: <position>R<delim><rseq>
        """
        rowA = "%s: %dF%c%s%c%d"%(self.chrom, self.pos,
                                  delim, self.fSeq,
                                  delim, self.size)
        rowB = "%s: %dR%c%s"%(self.chrom, self.pos,
                              delim, self.rSeq)
        return (rowA + "\n" + rowB)
