#!/usr/bin/env python

# common
import csv
import os
import sys
import time
import uuid

# less common
import twobitreader
import requests
import xlrd
from bs4 import BeautifulSoup

# flask
from flask import (Flask, request, render_template, redirect, url_for,
    send_from_directory, flash, jsonify, session, g)
from werkzeug.utils import secure_filename

# local modules
from parseform import getFormDefaults
from decorators import async
from pclass import Primer
from appsecret import SECRET_KEY

__author__ = "Joe Carli"
__copyright__ = "Copyright 2014"
__credits__ = ["Joe Carli"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Joe Carli"
__email__ = "jrcarli@gmail.com"
__status__ = "Development"

ALLOWED_EXTENSIONS = set(['txt','csv','xls','xlsx'])

app = Flask(__name__)
app.config.update(dict(
    SECRET_KEY=SECRET_KEY,
    DEBUG=False,
    UPLOAD_FOLDER = "/tmp",
    GB_URL = "http://genome.ucsc.edu",
    P3_URL = "http://bioinfo.ut.ee",
    GB = '',
    STATUS='ONLINE',
    ))

#TODO: make this part of the g obj
_sessionPrimers = {}
_warnings = {}

def getDummyPrimers(sessionId):
    """Handy dummy function when working offline."""
    global _sessionPrimers
    pA = Primer('chr1',808984,'GATACA','GATACA',100)
    pB = Primer('chr1',909984,'TACATACA','TACATACA',200)
    time.sleep(8)
    _sessionPrimers[sessionId].extend([pA,pB])
# end of returnDummyPrimers()

def createSession():
    global _sessionPrimers
    global _warnings
    session['uuid'] = str(uuid.uuid4()) 
    _sessionPrimers[session['uuid']] = []
    _warnings[session['uuid']] = []
    
def endSession():
    global _sessionPrimers
    global _warnings
    _sessionPrimers.pop(session['uuid'],None)
    _warnings.pop(session['uuid'],None)
    session.pop('uuid', None)

def readCsv(filename):
    """Reads a csv and returns a list of dictionaries."""
    rows = [] # a list of dictionaries
    with open(filename,'rb') as f:
        csvReader = csv.DictReader(f, delimiter=',', quotechar='|')
        for row in csvReader:
            rows.append(row)
    return rows
# end of readCsv()

def readExcel(filename):
    """Reads a xsl or xslx file and returns a list of dictionaries."""
    rows = []
    header = []
    book = xlrd.open_workbook(filename)
    sheet = book.sheet_by_index(0)
    # first read the keys (i.e., the col headers)
    for i in range(0,sheet.ncols):
        header.append(str(sheet.cell_value(0,i)))
    # create a dict for each row
    for rowIndex in range(1,sheet.nrows):
        rowDict = dict()
        for colIndex,colName in enumerate(header):
            cellType = sheet.cell_type(rowIndex,colIndex)
            if cellType == 1: # text 
                cellValue = str(sheet.cell_value(rowIndex,colIndex))
            elif cellType == 2: # number
                cellValue = int(float(sheet.cell_value(rowIndex,colIndex)))
            else:
                print "readExcel() Error!: Unexpected type %d at row %d col %d"%(cellType,rowIndex,colIndex)
            rowDict[str(colName)] = cellValue #str(sheet.cell_value(rowIndex,colIndex))
        rows.append(rowDict)
    return rows
# end of readExcel()

def primersToCsv(primerList,outfile,delim=','):
    #print "Writing %d primers to %s"%(len(primerList),outfile)
    with open(outfile,'wb') as f:
        f.write('Name%cSequence%cSize\n'%(delim,delim))
        for primer in primerList:
            output = str(primer)
            f.write(output+"\n")
# end of primersToCsv()
        
def gb_getSessionId():
    """Creates a new session with the UCSC Genome Browser.
    Returns the session ID (hgsid) as a string. Returns an
    empty string if an error occurs.
    """
    url = "/".join([app.config['GB_URL'], "cgi-bin", "hgGateway"])
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


#genomeRef = gb_getSequence(hgsid,db,chrom,int(pos)-1,int(pos))
#def getSequence(genome,chromosome,sequenceStart,sequenceEnd):
def gb_getSequence(hgsid,db='hg19',chrom='chr1',
    left=808983,right=808984,
    leftPad=500,rightPad=500):
    """Returns a sequence ..."""
    
    # for instance: pos="chr1:808984-808984"
    posDelta = right - left - 1
    pos = "%s:%d-%d"%(chrom,right-posDelta,right)

    url = "/".join([app.config['GB_URL'], "cgi-bin", "hgc"])
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

def bracketSequence(seq,left=400,right=600):
    s = seq[0:left]
    s = s + "["
    s = s + seq[left:right]
    s = s + "]"
    s = s + seq[right:]
    return s
# end of bracketSequence()

def getPrimer(bSeq,chrom='UNKNOWN',pos=-1,primerlen='200-500'):
    """bSeq is a bracketed sequence."""
    #print "in getPrimer()"   
    #print "chrom: %s"%(chrom)
    #print "pos: %d"%(pos)
    url = "/".join([app.config['P3_URL'],"primer3-0.4.0"])
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
    params = getFormDefaults(form)
    
    url = "/".join([app.config['P3_URL'],"cgi-bin",
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

@async
def processRows(sessionId,rows,genomeFile,
    db='hg38',
    chromcol='#CHROM',poscol='POS',refcol='REF',
    bracketlen=500,primerlen='200-500'):
    global _sessionPrimers
    global _warnings

    if app.config['STATUS'] == 'OFFLINE':
        return getDummyPrimers(sessionId)

    for idx,row in enumerate(rows):
        if chromcol not in row or \
            poscol not in row or \
            refcol not in row:
            print "~"*20+" MISSING COL IN ROW "+"~"*20
            print row
            warn = ("Error! Row %d could not be parsed. Skipping."%(idx+1))
            _warnings[sessionId].append(warn)
            _sessionPrimers[sessionId].append(
                Primer('ERROR',-1,'ERROR','ERROR',-1))
            continue
         
        pos = row[poscol]
        ref = row[refcol]
        pos_int = 0
        ref_char = '' 
        chrom = "chr%s"%(row[chromcol])
        warn = ("Error! Found '%s' in %s column of row %d; expected "
            "1-22, X, or Y. Skipping."%(row[chromcol],chromcol,idx+1))
        # assume that chrom is 1-22, X or Y
        try:
            chrom_int = int(row[chromcol])
            if chrom_int < 1 or chrom_int > 22:
                print warn
                _warnings[sessionId].append(warn)
                _sessionPrimers[sessionId].append(
                    Primer('ERROR',-1,'ERROR','ERROR',-1))
                continue
        except:
            chrom_str = row[chromcol].lower()
            if chrom_str!='x' and chrom_str!='y':
                print warn    
                _warnings[sessionId].append(warn)
                _sessionPrimers[sessionId].append(
                    Primer('ERROR',-1,'ERROR','ERROR',-1))
                continue

        # test that pos is an int
        try:
            pos_int = int(pos)
        except:
            warn = ("Error! Found '%s' in %s column of row %d; expected "
                "an integer. Skipping."%(pos,poscol,idx+1))
            print warn
            _warnings[sessionId].append(warn)
            _sessionPrimers[sessionId].append(
                Primer('ERROR',-1,'ERROR','ERROR',-1))
            continue

        # test that ref is a single character in A,C,T,G
        lowerRef = ref.lower()
        if len(lowerRef) > 1 or \
            (lowerRef!='a' and lowerRef!='c' 
            and lowerRef!='t' and lowerRef!='g'):
            warn = ("Error! Found '%s' in %s column of row %d; expected "
                "A, C, T, or G. Skipping."%(ref,refcol,idx+1))
            _warnings[sessionId].append(warn)
            _sessionPrimers[sessionId].append(
                Primer('ERROR',-1,'ERROR','ERROR',-1))
            continue

        # 0 indexed so get [pos-1:pos] for the reference
        # treat pos as a str that may have .0 if it came from an excel file
        # int(float('10.0')) will return 10
        # int('10.0') will produce an error
        #genomeRef = getSequence(genome,chrom,int(float(pos))-1,int(float(pos)))
        hgsid = ''
        if app.config['GB'] == 'UCSC':
            hgsid = gb_getSessionId()
            #genomeRef = gb_getSequence(hgsid,db,chrom,int(pos)-1,int(pos))
            genomeRef = gb_getSequence(hgsid,db=db,chrom=chrom,
                left=(int(pos)-1),right=(int(pos)),
                leftPad=0,rightPad=0)
        else:
            genome = loadGenome(genomeFile)
            genomeRef = getSequence(genome,chrom,int(pos)-1,int(pos))
        if genomeRef != ref:
            warn = ("Warning! Reference '%s' for chromosome %s, "
                "position %s was found to be '%s' in the genome file."
                %(ref,chrom,pos,genomeRef))
            print warn
            _warnings[sessionId].append(warn)

        seqStart = int(pos) - bracketlen - 1 
        seqEnd = seqStart + bracketlen + bracketlen + 1 
        # UCSC defaults to all upper case
        if app.config['GB'] == 'UCSC':
            #seq = gb_getSequence(hgsid,db,chrom,seqStart,seqEnd)
            seq = gb_getSequence(hgsid,db=db,chrom=chrom,
                left=(int(pos)-1),right=(int(pos)),
                leftPad=500,rightPad=500)

        else:
            seq = getSequence(genome,chrom,seqStart,seqEnd)
        bseq = bracketSequence(seq).upper() 
        primer = getPrimer(bseq,chrom,int(pos),primerlen)
        if primer == None:
            print "getPrimer returned None!!"
        _sessionPrimers[sessionId].append(primer)

    #print "processRows(): %d Primers created"%(len(_sessionPrimers[sessionId]))
# end of processRows()

@app.route('/status', methods=['GET'])
def getStatus():
    global _sessionPrimers
    global _warnings
    if session['uuid'] in _sessionPrimers:
        curLen = len(_sessionPrimers[session['uuid']])
    else:
        curLen = 0
    if 'totalRows' not in session:
        session['totalRows'] = -1

    warnings = []
    if session['uuid'] in _warnings:
        warnings.extend(_warnings[session['uuid']])

    return jsonify({'totalRows':str(session['totalRows']),
        'curRow':str(curLen), 'uuid':session['uuid'],
        'warnings':warnings})
# end of getStatus()

def allowed_file(filename):
    global ALLOWED_EXTENSIONS
    return '.' in filename and \
        filename.rsplit('.',1)[1] in ALLOWED_EXTENSIONS
# end of allowed_file()

@app.route('/getfile/<filename>')
def get_file(filename):
    global _sessionPrimers
    #expectedFilename = ".".join([session['uuid'],'csv'])
    #if filename != expectedFilename:
    #    flash("Error: Bad session ID.")
    #    return redirect(url_for('upload_file'))
    # make sure to create the filename locally so we can end the session
    #filename = filename + ".csv"
    path = os.path.join(app.config['UPLOAD_FOLDER'],filename)
    primersToCsv(_sessionPrimers[session['uuid']],path)
    endSession()
    return send_from_directory(app.config['UPLOAD_FOLDER'],filename)
# end of get_file()

@app.route('/', methods=['GET','POST'])
def upload_file():
    if request.method == 'POST':
        session['db'] = 'hg38' # use the latest genome by default
        if 'db' in request.form:
            if request.form['db'] == 'hg19':
                session['db'] = 'hg19'
            elif request.form['db'] != 'hg38':
                flash('Unsuported genome option %s. Using hg38.'
                    %(request.form['session']))
        else:
            flash('Genome not specified. Using hg38.')

        # Set up the Spreadhseet Column for this run
        session['chromcol'] = '#CHROM'
        session['poscol'] = 'POS'
        session['refcol'] = 'REF'
        if 'chromcol' in request.form and \
            request.form['chromcol'] != session['chromcol']:
            session['chromcol'] = request.form['chromcol']
            flash("Using %s as chromosome column name"%(session['chromcol']))
        if 'poscol' in request.form and \
            request.form['poscol'] != session['poscol']:
            session['poscol'] = request.form['poscol']
            flash("Using %s as position column name"%(session['poscol']))
        if 'refcol' in request.form and \
            request.form['refcol'] != session['refcol']:
            session['refcol'] = request.form['refcol']
            flash("Using %s as reference column name"%(session['refcol']))

        # Set up the Sequence Options for this run
        session['bracketlen'] = 500
        session['primerlen'] = '200-500'
        if 'bracketlen' in request.form and \
            int(request.form['bracketlen']) != session['bracketlen']:
            session['bracketlen'] = int(request.form['bracketlen'])
            flash("Using %d as bracketed sequence length"%(session['bracketlen']))
        if 'primerlen' in request.form and \
            request.form['primerlen'] != session['primerlen']:
            session['primerlen'] = request.form['primerlen']
            flash("Using %s as Primer3 sequence length range"%(session['primerlen']))

        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'],filename)
            file.save(path)
            createSession()
            session['filename'] = filename
            if filename[-3:] == 'csv':
                rows = readCsv(path)
            else:
                rows = readExcel(path)
            session['totalRows'] = len(rows)
            genomePath = "genomes"
            if session['db'] == 'hg19':
                genomeFile = "hg19.2bit"
            else:
                session['db'] = 'hg38'
                genomeFile = "hg38.2bit"
            genomeFilePath = "/".join([genomePath,genomeFile])
            processRows(session['uuid'],rows,genomeFilePath,
                db=session['db'],
                chromcol=session['chromcol'],poscol=session['poscol'],
                refcol=session['refcol'],
                bracketlen=session['bracketlen'],
                primerlen=session['primerlen'])
            return render_template('status.html')
        else:
            if not file:
                flash("You must specify a file.")
            else:
                flash("Invalid filename. File extensions may include: %s."%
                    (", ".join(ALLOWED_EXTENSIONS)))
    # if not post, return index.html
    return render_template('index.html')#,primerList=session['primerList'])
# end of upload_file()

def testProcessing(genomeFilePath):
    rows = readCsv('test.csv')
    primerList = []
    #TODO: this is busted - first elem needs to be session id
    processRows(primerList,rows,genomeFilePath)
    for p in primerList:
        print p

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
    primersToCsv(primerList)

if __name__ == "__main__":
    if True:
        app.run(host='0.0.0.0',port=80)
    else:
        genomePath = 'genomes'
        genomeFile = 'hg19.2bit'
        genomeFilePath = "/".join([genomePath,genomeFile])
        testGetSequence(genomeFilePath)

