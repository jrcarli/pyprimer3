"""Helper functions to work with Primer3.

Interacts with Primer3 at http://bioinfo.ut.ee.
"""

import requests
from bs4 import BeautifulSoup

# local modules
import parseform 
from pclass import Primer

__author__ = "Joe Carli"
__copyright__ = "Copyright 2014"
__credits__ = ["Joe Carli"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Joe Carli"
__email__ = "jrcarli@gmail.com"
__status__ = "Development"

P3_URL = "http://bioinfo.ut.ee"

def getPrimer(bSeq,chrom='UNKNOWN',pos=-1,primerlen='200-500'):
    """bSeq is a bracketed sequence."""
    url = "/".join([P3_URL,"primer3-0.4.0"])
    r = requests.get(url)
    if r.status_code != 200:
        print "getPrimer(): Retrieving %s failed, status code %d" \
            %(url,r.status_code)
        return None
    soup = BeautifulSoup(r.text)
    forms = soup.find_all('form',
        {'action':'/cgi-bin/primer3-0.4.0/primer3_results.cgi'},limit=1)
    if len(forms) <= 0:
        print "getPrimer(): Unable to find form in html"
        return None
    form = forms[0]
    params = parseform.getFormDefaults(form)
    
    url = "/".join([P3_URL,"cgi-bin",
        "primer3-0.4.0","primer3_results.cgi"])
    
    # override a few default params
    params['PRIMER_MISPRIMING_LIBRARY'] = 'HUMAN'
    params['PRIMER_PRODUCT_SIZE_RANGE'] = primerlen 
    params['Pick Primers'] = 'Pick Primers'
    params['SEQUENCE'] = bSeq

    #print "POSTing to primer3"
    r = requests.post(url,params)

    if r.status_code != 200:
        print "POST to primer3 returned %d"%(r.status_code)
    #else:
    #    print "POST to primer3 has returned data"
    soup = BeautifulSoup(r.text)
    preTags = soup.find_all('pre',limit=1)
    if len(preTags) <= 0:
        print "getPrimer(): Failed to find <pre> tags in response"
        return None
    
    pre = preTags[0]
    for contents in pre.contents:
        if 'LEFT PRIMER' in contents:
            leftStart = contents.find('LEFT PRIMER')
            leftEnd = contents.find('\n',leftStart)
            rightStart = contents.find('RIGHT PRIMER')
            rightEnd = contents.find('\n',rightStart)
        
            leftPrimerStart = contents.rfind(' ',leftStart,leftEnd)
            rightPrimerStart = contents.rfind(' ',rightStart,rightEnd)
            
            leftPrimer = contents[leftPrimerStart+1:leftEnd]
            rightPrimer = contents[rightPrimerStart+1:rightEnd]
    
            productSizeLoc = contents.find('PRODUCT SIZE:')
            productSizeEnd = contents.find(',',productSizeLoc)
            productSizeStart = \
                contents.rfind(' ',productSizeLoc,productSizeEnd)
            productSize = int(contents[productSizeStart+1:productSizeEnd])
            #return (leftPrimer,rightPrimer,productSize)
            #print "Creating Primer obj"
            myprimer = Primer(chrom,pos,leftPrimer,rightPrimer,productSize)
            #print myprimer
            #print "Returing Primer obj"
            return myprimer
        #else:
        #    print "DID NOT FIND 'LEFT PRIMER' in return from primer3"
        #    print "~"*50
        #    print contents
        #    print "\n\n"
    # else return error
    print "final error handler in getPrimer()"
    print "~"*50
    return None
# end of getPrimer()

