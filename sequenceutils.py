"""Helper routines for working with genomic sequences.

Uses the twobitreader module for working with .2bit files.
"""

import twobitreader

__author__ = "Joe Carli"
__copyright__ = "Copyright 2014"
__credits__ = ["Joe Carli"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Joe Carli"
__email__ = "jrcarli@gmail.com"
__status__ = "Development"


def loadGenome(genomeFilePath):
    """Return a TwoBitFile object given a particular .2bit filename."""
    return twobitreader.TwoBitFile(genomeFilePath)
# end of loadGenome()

def getSequence(genome, chromosome, sequenceStart, sequenceEnd):
    """Return a sequence (substring) from a particular chromosome of a 
    particular genome.

    The genome input is expected to be a TwoBitFile object.
    The chromosome input should be formatted as 'chr1' or 'chrX'.
    The sequenceStart and sequenceEnd inputs are integers.
    """
    # find the appropriate chromosome
    chrom = genome[chromosome]

    # find the appropriate sequence
    seq = chrom[sequenceStart:sequenceEnd]
    
    # return the sequence
    return seq
# end of getSequence()

def bracketSequence(seq,left=400,right=600):
    """Insert left and right brackets into a genomic sequence (string)
    at provided offsets.

    left (input) is the offset where '[' is inserted.
    right (input) is the offset where ']' is inserted.
    The sequence string with inserted brackets is returned.
    """ 
    s = seq[0:left]
    s = s + "["
    s = s + seq[left:right]
    s = s + "]"
    s = s + seq[right:]
    return s
# end of bracketSequence()

