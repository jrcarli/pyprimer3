"""Testing functions to verify local .2bit file usage is equivalent
to UCSC Genome Browser usage.
"""

import uuid

from pclass import Primer
import sequenceutils
import fileutils
import genomebrowser
import webprimer3

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
    genome = sequenceutils.loadGenome(genomeFilePath)
    seqA = sequenceutils.getSequence(genome,chrom,seqStart,seqEnd)
    seqA = seqA.upper()
    print seqA

    print "~"*50    

    # get sesion id
    print "Getting sesion id ..."
    hgsid = genomebrowser.gb_getSessionId()
    print hgsid
    if hgsid == "":
        print "blank hgsid. quitting"
        sys.exit(1)
    seqB = genomebrowser.gb_getSequence(hgsid)
    print seqB

    print "~"*50

    if seqA == seqB:
        print "Sequences match!"
    else:
        print "Sequences do not match :("

    bseqA = sequenceutils.bracketSequence(seqA)
    bseqB = sequenceutils.bracketSequence(seqB)
    
    if bseqA != bseqB:
        print "Bracketed sequences do not match!"
        sys.exit(1)

    primerA = webprimer3.getPrimer(bseqA,chrom,int(seq))
    primerB = webprimer3.getPrimer(bseqB,chrom,int(seq))
   
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
    fileutils.primersToCsv(primerList,outfile)
    print "Wrote %s"%(outfile)

def getSequence():
    with open('sequence.txt','rb') as f:
        seq = f.read()
    return seq

if __name__=="__main__":
    genomePath = 'genomes'
    genomeFile = 'hg19.2bit'
    genomeFilePath = "/".join([genomePath,genomeFile])
    testGetSequence(genomeFilePath)
