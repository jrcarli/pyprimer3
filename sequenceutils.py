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
    return twobitreader.TwoBitFile(genomeFilePath)
# end of loadGenome()

def getSequence(genome,chromosome,sequenceStart,sequenceEnd):
    """chromosome should be formatted as 'chr1'"""
    # find the appropriate chromosome
    chrom = genome[chromosome]

    # find the appropriate sequence
    seq = chrom[sequenceStart:sequenceEnd]
    
    # return the sequence
    return seq
# end of getSequence()

def bracketSequence(seq,left=400,right=600):
    s = seq[0:left]
    s = s + "["
    s = s + seq[left:right]
    s = s + "]"
    s = s + seq[right:]
    return s
# end of bracketSequence()

