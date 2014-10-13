"""Helper functions to work with fruitfly.org NNSPLICE."""

import requests
from bs4 import BeautifulSoup

# local modules
import parseform 
from splicesite import SpliceSite

__author__ = "Joe Carli"
__copyright__ = "Copyright 2014"
__credits__ = ["Joe Carli"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Joe Carli"
__email__ = "jrcarli@gmail.com"
__status__ = "Development"

FF_URL = "http://www.fruitfly.org"

def parseHelper(line,startPos):
    # parse the start number
    grab = False
    value = ''
    for i,c in enumerate(line[startPos:]):
        if c==' ' or c=='\n' or c=='\r':
            if grab == True:
                break
        elif c.isdigit() or c=='.':
            grab = True
            value += c
        elif c.lower() in ['a','g','t','c']:
            grab = True
            value += c
        else:
            print("Error in parseHelper! "
                "Expected [0-9.actg] but saw %c in %s"%(c,line))
            break
    return (value,i+startPos)

def parseIntron(line):
    """Parse an intron line.
   
    Expect input (line) of the form:
       3    43     0.43     ggtacttctcctatacttt

    Return a tuple of (start,end,score,intron)
    ex: (int(3), int(43), float(0.43), str('ggtacttctcctatacttt'))
    """ 
    (startVal, startEnd) = parseHelper(line, 0)
    (endVal, startScore) = parseHelper(line, startEnd)
    (scoreVal, startIntron) = parseHelper(line, startScore)
    (intronVal, dontcare) = parseHelper(line, startIntron)

    ss = SpliceSite(int(startVal),
                    int(endVal),
                    float(scoreVal),
                    intronVal,
                    '')
    return ss
# end of parseIntron()

def parseExon(line,intron):
    pass

def getSpliceSitePredictions(seq):
    """seq is a genomic sequence."""
    # What we return
    spliceSiteList = []

    url = "/".join([FF_URL, 'seq_tools', 'splice.html'])
    r = requests.get(url)
    if r.status_code != 200:
        print("getSpliceSitePredictions(): Retrieving %s failed, "
            "status code %d"%(url,r.status_code))
        return None
    soup = BeautifulSoup(r.text)
    forms = soup.find_all('form',
        {'action':'/cgi-bin/seq_tools/splice.pl'},limit=1)
    if len(forms) <= 0:
        print "getSpliceSitePredictions(): Unable to find form in html"
        return None
    form = forms[0]
    #params = parseform.getFormDefaults(form)
    params = {}
    
    url = "/".join([FF_URL,"cgi-bin", "seq_tools", "splice.pl"])
    
    # override a few default params
    params['organism'] = 'human'
    params['which'] = 'both'
    params['reverse'] = 'yes' 
    params['min_donor'] = '0.1'
    params['min_acc'] = '0.1'
    params['text'] = seq
    params['submit'] = ' Submit ' # yes, the extra spaces are important!

    # POST away!
    r = requests.post(url,params)

    if r.status_code != 200:
        print "POST to fruitfly returned %d"%(r.status_code)
        return None

    # find 'Acceptor site predictions for' in the response
    acceptorLoc = r.text.find('Acceptor site predictions for')
    if acceptorLoc < 0:
        print("getSpliceSitePredictions(): Failed to find 'Acceptor site "
            "predictions for' in the response text.")
        print "~"*50
        print r.text
        return None

    # go to the first <pre> tag following our string
    # note: the following method will include our string but oh well
    soup = BeautifulSoup(r.text[acceptorLoc:])
    preTags = soup.find_all('pre',limit=1)
    if len(preTags) <= 0:
        print "getSpliceSitePredictions(): Failed to find <pre> tags in response"
        return None
   
    pre = preTags[0]
    contents = pre.renderContents()

    # normalize line breaks (i don't know why ec2 is getting odd tags)
    # ORDER MATTERS
    # git rid of weird break tags that show up with ec2
    contents = contents.replace('</br>','')
    # normalize old style br to new style br
    contents = contents.replace('<br>','<br/>')
    # change all line breaks to new lines
    contents = contents.replace('<br/>','\n')

    # remove annoying font tags and add a space between intron and exon
    # ORDER MATTERS 
    # remove tags, add space between intron and exon
    contents = contents.replace('</font><font size="+2">',' ')
    # get rid of tag hanging out in the intron
    contents = contents.replace('<font size="+2">','')
    # and finally remove the closing tag from the exon
    contents = contents.replace('</font>','')
 
    # Now we can easily split by newline 
    # could have done this on <br/> but cleaner to print out results for debug
    lines = contents.split("\n")

    if len(lines) <= 1:
        print "Error: Expected multiple lines but found only one."
        print lines
        return []

    # lines[0] is the header so skip
    for line in lines[1:]:
        # change all multiple spaces to single spaces 
        normalizedLine = ''

        # strip leading and trailing whitespace
        line = line.strip()
        if len(line) <= 0:
            continue

        for i,c in enumerate(line):
            # if not space, add character
            if c!=' ':
                normalizedLine = normalizedLine + c
            else:
                if i < (len(line)-1):
                    # if next spot is a space, ignore this one
                    if line[i+1] == ' ':
                        continue
                    # if next spot is not a space, take this space
                    else:
                        normalizedLine = normalizedLine + c
                # else: don't care about ending space

        #print normalizedLine
        # now we can split the line by space and have all our SpliceSite parts
        parts = normalizedLine.split(' ')
        if len(parts) != 5:
            print "Error: bad line! Expected 5 parts."
            print normalizedLine
            print parts
        else:
            spliceSiteList.append(SpliceSite(int(parts[0]),
                                             int(parts[1]),
                                             float(parts[2]),
                                             parts[3],
                                             parts[4]))

    return spliceSiteList

    # ignore lines that start with '<','a','c','g', or 't'
    # lines we care about probably start with one or more spaces
    #ignoreAlphabet = ['s','<','a','c','g','t']
    ignoreAlphabet = ['s','<']
    for i,contents in enumerate(pre.contents):
        if contents==None or len(contents) <= 0 or contents.string==None:
            continue

        # skip lines we don't care about
        # we will want to care about <font> lines
        #lc = contents.lower()
        #if lc[0] in ignoreAlphabet:
        lc = contents.string.lower() 

        if lc[0] in ignoreAlphabet:
            continue

        if lc[0] in ['a','c','g','t']:
            if len(lc)==1:
                #print "NEED TO PROCESS BOUNDARY:\n\t'%s'"%(lc)
                #continue
                if len(spliceSiteList) <= 0:
                    print "ERORR: Found bondary before intron"
                    break
                if spliceSiteList[-1].foundIntronBoundary:
                    spliceSiteList[-1].exon = contents.string
                else:
                    spliceSiteList[-1].intron += contents.string
                    spliceSiteList[-1].foundIntronBoundary = True
            else:
                #print "Need to process exon:\n\t'%s'"%(lc)
                #continue
                if len(spliceSiteList) <= 0:
                    print "ERROR: Found exon before intron"
                spliceSiteList[-1].exon += contents.string
        else:
            spliceSite = parseIntron(contents.string)
            spliceSiteList.append(spliceSite)
            #print spliceSite
    return spliceSiteList
# end of getSpliceSitePredictions()
