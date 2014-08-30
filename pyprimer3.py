#!/usr/bin/env python

"""Flask application for primer3 automation."""

# common
import os
import sys
import time
import uuid

# flask
from flask import (Flask, request, render_template, redirect, url_for,
    send_from_directory, flash, jsonify, session, g)
from werkzeug.utils import secure_filename

# local modules
import decorators 
import appsecret 
import sequenceutils 
import fileutils 
import genomebrowser 
import webprimer3 
from pclass import Primer

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
    SECRET_KEY=appsecret.SECRET_KEY,
    DEBUG=True,
    UPLOAD_FOLDER = "/tmp",
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

@decorators.async
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

        hgsid = ''
        if app.config['GB'] == 'UCSC':
            hgsid = genomebrowser.gb_getSessionId()
            genomeRef = genomebrowser.gb_getSequence(hgsid, db=db, chrom=chrom,
                                                     left=(int(pos)-1),
                                                     right=(int(pos)),
                                                     leftPad=0,
                                                     rightPad=0)
        else:
            genome = sequenceutils.loadGenome(genomeFile)
            genomeRef = sequenceutils.getSequence(genome, chrom,
                                                  int(pos)-1, int(pos))
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
            seq = genomebrowser.gb_getSequence(hgsid, db=db, chrom=chrom,
                                               left=(int(pos)-1),
                                               right=(int(pos)),
                                               leftPad=500,
                                               rightPad=500)
        else:
            seq = sequenceutils.getSequence(genome, chrom, seqStart, seqEnd)
        bseq = sequenceutils.bracketSequence(seq).upper() 
        primer = webprimer3.getPrimer(bseq, chrom, int(pos), primerlen)
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
    fileutils.primersToCsv(_sessionPrimers[session['uuid']],path)
    endSession()
    return send_from_directory(app.config['UPLOAD_FOLDER'],filename)
# end of get_file()

@app.route('/splicesite', methods=['GET','POST'])
def spliceSite():
    flash('Splice site prediction coming soon!')
    return render_template('index.html')
# end of spliceSite()

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
                rows = fileutils.readCsv(path)
            else:
                rows = fileutils.readExcel(path)
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

if __name__ == "__main__":
    if 0 == os.geteuid():
        app.run(host='0.0.0.0',port=80)
    else:
        app.run(host='0.0.0.0')
