import uuid

from pclass import Primer
from sequenceutils import loadGenome, getSequence, bracketSequence
from fileutils import readCsv, readExcel, primersToCsv
from genomebrowser import gb_getSessionId, gb_getSequence
from webprimer3 import getPrimer

__author__ = "Joe Carli"
__copyright__ = "Copyright 2014"
__credits__ = ["Joe Carli"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Joe Carli"
__email__ = "jrcarli@gmail.com"
__status__ = "Development"

def testGetSequence(genomeFilePath):
    chrom = 'chr1'
    seq = '808984'
    seqlen = 1
    seqStart = int(seq) - seqlen - 500
    seqEnd = seqStart + seqlen + 1000
    genome = loadGenome(genomeFilePath)
    seqA = getSequence(genome,chrom,seqStart,seqEnd)
    seqA = seqA.upper()
    print seqA

    print "~"*50    

    # get sesion id
    print "Getting sesion id ..."
    hgsid = gb_getSessionId()
    print hgsid
    if hgsid == "":
        print "blank hgsid. quitting"
        sys.exit(1)
    seqB = gb_getSequence(hgsid)
    print seqB

    print "~"*50

    if seqA == seqB:
        print "Sequences match!"
    else:
        print "Sequences do not match :("

    bseqA = bracketSequence(seqA)
    bseqB = bracketSequence(seqB)
    
    if bseqA != bseqB:
        print "Bracketed sequences do not match!"
        sys.exit(1)

    primerA = getPrimer(bseqA,chrom,int(seq))
    primerB = getPrimer(bseqB,chrom,int(seq))
   
    if primerA.fSeq != primerB.fSeq \
        or primerA.rSeq != primerB.rSeq \
        or primerA.size != primerB.size:
        print "Primer mismatch"
        print "primerA:"
        print primerA
        print "primerB:"
        print primerB
        sys.exit(1)
    else:
        print "Primer match"
        print primerA

    primerList = [primerA,primerB]

    outfile = "/tmp/"+str(uuid.uuid4())+".csv"
    primersToCsv(primerList,outfile)
    print "Wrote %s"%(outfile)

if __name__=="__main__":
    genomePath = 'genomes'
    genomeFile = 'hg19.2bit'
    genomeFilePath = "/".join([genomePath,genomeFile])
    testGetSequence(genomeFilePath)
