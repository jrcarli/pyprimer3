"""Helper functions for interacting with UCSC's Genome Browser."""

import requests
from bs4 import BeautifulSoup

__author__ = "Joe Carli"
__copyright__ = "Copyright 2014"
__credits__ = ["Joe Carli"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Joe Carli"
__email__ = "jrcarli@gmail.com"
__status__ = "Development"

GB_URL = "http://genome.ucsc.edu"

def gb_getSessionId():
    """Creates a new session with the UCSC Genome Browser.
    Returns the session ID (hgsid) as a string. Returns an
    empty string if an error occurs.
    """
    url = "/".join([GB_URL, "cgi-bin", "hgGateway"])
    r = requests.get(url)
    if r.status_code != 200:
        print "getSession(): Retrieval of %s returned %d"%(url,r.status_code)
        return ''
    soup = BeautifulSoup(r.text)
    inputs = soup.find_all('input',{'name':'hgsid'},limit=1)
    if len(inputs) <= 0:
        print "getSession(): Could not find an input tag with name 'hgsid'"
        return ''
    hgsid = inputs[0].get('value')
    return hgsid
# end of gb_getSessionId()

def gb_getSequence(hgsid,db='hg19',chrom='chr1',
    left=808983,right=808984,
    leftPad=500,rightPad=500):
    """Returns a sequence ..."""
    
    # for instance: pos="chr1:808984-808984"
    posDelta = right - left - 1
    pos = "%s:%d-%d"%(chrom,right-posDelta,right)

    url = "/".join([GB_URL, "cgi-bin", "hgc"])
    url = url + "?hgsid=" + hgsid
    url = url + "&g=htcGetDna2"
    url = url + "&table="
    url = url + "&i=mixed"
    url = url + "&o=" + str(left)
    url = url + "&l=" + str(left)
    url = url + "&r=" + str(right)
    url = url + "&getDnaPos=" + pos
    url = url + "&db=" + db
    url = url + "&c=" + chrom
    url = url + "&hgSeq.cdsExon=1"
    url = url + "&hgSeq.padding5=" + str(leftPad)
    url = url + "&hgSeq.padding3=" + str(rightPad)
    url = url + "&hgSeq.casing=upper"
    url = url + "&boolshad.hgSeq.maskRepeats=0"
    url = url + "&hgSeq.repMasking=lower"
    url = url + "&boolshad.hgSeq.revComp=0"
    url = url + "&submit=get+DNA"

    r = requests.post(url)
    # this string immediately preceds the sequence
    repMask = "repeatMasking=none\n"
    start = r.text.find(repMask) + len(repMask)
    # this string immediately follows the sequence
    endPre = "</PRE>"
    end = r.text.find(endPre,start)
    seq = r.text[start:end]
    # remove the newline characters
    seq = seq.replace("\n","")
    return seq
# end of gb_getSequence()

