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

# celery
from celery import Celery
from celery.utils.log import get_task_logger

# redis
import redis

# local modules
#import decorators 
import appsecret 
import sequenceutils 
import fileutils 
import fruitfly
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

# Celery configuration
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

# Initialize Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)
logger = get_task_logger(app.name)

# Initialize Redis connection
redis_server = redis.Redis(app.config['CELERY_RESULT_BACKEND'])

def createSession():
    """TODO: Remove if not useful"""
    return
    session['uuid'] = str(uuid.uuid4()) 

def endSession():
    """TODO: Remove if not useful"""
    return
    session.pop('uuid', None)

@celery.task(bind=True)
def predictSpliceSites(self,
                       rows,
                       genomeFile,
                       db='hg38',
                       chromcol='#CHROMCOL',
                       poscol='POS',
                       varcol='VARIANT'):
    # celery kung fu
    self.predictions = list()
    #self.warnings = list()
    warnings = list()
    task_id = predictSpliceSites.request.id

    rowCount = len(rows)

    for idx,row in enumerate(rows):
        logger.info('Processing row %d'%(idx))
        warnings.append('Processing row %d'%(idx))
        chrom = "chr%s"%(row[chromcol])
        seqStart = int(row[poscol]) - 501
        seqEnd = int(row[poscol]) + 500
        genome = sequenceutils.loadGenome(genomeFile)
        seq = sequenceutils.getSequence(genome, chrom, seqStart, seqEnd)

        # make a copy of seq but with the base modified at specified position
        # python doesn't support item assignments w/in strings so build pieces
        var = seq[0:500]
        var = var + row[varcol]
        var = var + seq[501:]

        expectedSites = fruitfly.getSpliceSitePredictions(seq)
        variantSites = fruitfly.getSpliceSitePredictions(var)

        expectedList = []
        variantList = []
        msgList = []

        # not used ... yet
        for ss in expectedSites:
            expectedList.append([ss.start,
                                 ss.end,
                                 ss.score,
                                 ss.intron,
                                 ss.exon])

        for ss in variantSites:
            variantList.append([ss.start,
                                ss.end,
                                ss.score,
                                ss.intron,
                                ss.exon])

        for i, variantSite in enumerate(variantSites):
            (posB,baseB,scoreB) = variantSite.getSpliceSite()
            foundMatch = False
            for j, expectedSite in enumerate(expectedSites):
                (posA,baseA,scoreA) = expectedSite.getSpliceSite()
                if posA==posB:
                    foundMatch = True
                    if scoreA==scoreB:
                        if baseA != baseB:
                            #flash("Base changed from %s to %s at position %d "
                            #    "with score %0.2f\n"%(baseA, baseB, posA, scoreA))
                            warn = ("Base changed from %s to %s at position %d "
                                    "with score %0.2f"%(baseA,baseB,posA,scoreA))
                            warnings.append(warn)
                    else:
                        delta = abs(scoreA - scoreB)
                        if delta >= 0.4:
                            #flash("Score changed by %0.2f from %0.2f to %0.2f "
                            #    "at position %d.\n"%(delta, scoreA, scoreB, posA))
                            warn = ("Score changed by %0.2f from %0.2f to %0.2f "
                                    "at position %d."%(delta,scoreA,scoreB,posA))
                            warnings.append(warn)
            if not foundMatch:

                if posB >= len(seq):
                    #flash("Oops! Somehow the length of our expected and varied "
                    #    "sequences is not equivalent (%d for expected, "
                    #    "%d for varied).\n"%(len(seq),len(var)))
                    warn = ("Oops! Somehow the length of our expected and varied "
                            "sequences is not equivalent (%d for expected, "
                            "%d for varied)."%(len(seq),len(var)))
                    warnings.append(warn)
                    break
                origBase = seq[posB].lower()

                msgList.append("New splice site predicted at position %d with score %0.2f. "
                    "Original base was '%s' and new base is '%s'."
                    %(posB, scoreB, origBase, baseB))

                # Add to the session predictions list
                self.predictions.append(variantSite) 

    logger.debug('Creating output file ...')
    filename = str(task_id) + '.csv' 
    path = os.path.join(app.config['UPLOAD_FOLDER'],filename)
    logger.debug('Filename: %s'%(filename))
    logger.debug('Path: %s'%(path))
    fileutils.predictionsToCsv(self.predictions,path)
    logger.debug('Done writing to file')

    logger.info('Returning result')
    return {'current': rowCount, 'total': rowCount, 'warnings': warnings } 

# end of predictSpliceSites()

@celery.task(bind=True)
def processRows(self,rows,genomeFile,
    db='hg38',
    chromcol='#CHROM',poscol='POS',refcol='REF',
    bracketlen=500,primerlen='200-500'):

    # celery kung fu
    self.primers = list()
    #self.warnings = list()
    warnings = list()
    task_id = processRows.request.id

    rowCount = len(rows)

    for idx,row in enumerate(rows):
        logger.info('Processing row %d'%(idx)) 
        warnings.append('Processing row %d'%(idx))
        if chromcol not in row or \
            poscol not in row or \
            refcol not in row:
            print "~"*20+" MISSING COL IN ROW "+"~"*20
            print row
            warn = ("Error! Row %d could not be parsed. Skipping."%(idx+1))
            warnings.append(warn)
            self.primers.append(Primer('ERROR',-1,'ERROR','ERROR',-1))
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
                logging.warning(warn)
                warnings.append(warn)
                self.primers.append(
                    Primer('ERROR',-1,'ERROR','ERROR',-1))
                continue
        except:
            chrom_str = row[chromcol].lower()
            if chrom_str!='x' and chrom_str!='y':
                logging.warning(warn)   
                warnings.append(warn)
                self.primers.append(
                    Primer('ERROR',-1,'ERROR','ERROR',-1))
                continue

        # test that pos is an int
        try:
            pos_int = int(pos)
        except:
            warn = ("Error! Found '%s' in %s column of row %d; expected "
                "an integer. Skipping."%(pos,poscol,idx+1))
            logging.warning(warn)
            warnings.append(warn)
            self.primers.append(
                Primer('ERROR',-1,'ERROR','ERROR',-1))
            continue

        # test that ref is a single character in A,C,T,G
        lowerRef = ref.lower()
        if len(lowerRef) > 1 or \
            (lowerRef!='a' and lowerRef!='c' 
            and lowerRef!='t' and lowerRef!='g'):
            warn = ("Error! Found '%s' in %s column of row %d; expected "
                "A, C, T, or G. Skipping."%(ref,refcol,idx+1))
            logging.warning(warn)
            warnings.append(warn)
            self.primers.append(
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
            logging.warning(warn)
            warnings.append(warn)

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
            logging.warning('getPrimer returned None')
        self.primers.append(primer)
        logger.debug('Updating state for task id %s'%(str(task_id)))
        self.update_state(state='PROGRESS', meta={'current':idx, 'total': rowCount, 'warnings': warnings}) 
    
    logger.debug('Creating output file ...')
    filename = str(task_id) + '.csv' 
    path = os.path.join(app.config['UPLOAD_FOLDER'],filename)
    logger.debug('Filename: %s'%(filename))
    logger.debug('Path: %s'%(path))
    fileutils.primersToCsv(self.primers,path)
    logger.debug('Done writing to file')

    logger.info('Returning result')
    return {'current': rowCount, 'total': rowCount, 'warnings': warnings } 

# end of processRows()

@app.route('/status/<myfunc>/<task_id>', methods=['GET'])
def getStatus(myfunc,task_id):
    myfunc = myfunc.lower()
    if myfunc == 'primers':
        task = processRows.AsyncResult(task_id)
    elif myfunc == 'predictions':
        task = predictSpliceSites.AsyncResult(task_id)
    else:
        print("Unexpected myfunc variable: %s"%(myfunc))
        flash("Unexpected URL. Cannot identify task status.")
        return render_template('index.html')

    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'warnings': [], 
        }
    elif task.state != 'FAILURE':
        warnings = []
        if 'warnings' in task.result:
            warnings = task.result['warnings']
        response = {
            'state': task.state,
            'current': task.info.get('current',0),
            'total': task.info.get('total', 1),
            'warnings': warnings, 
        }
    else:
        # something went wrong in the background job
        warnings = []
        if 'warnings' in task.result:
            warnings = task.result['warnings']
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'warnings': [],#warnings, 
        }
    return jsonify(response) 

# end of getStatus()

def allowed_file(filename):
    global ALLOWED_EXTENSIONS
    return '.' in filename and \
        filename.rsplit('.',1)[1] in ALLOWED_EXTENSIONS
# end of allowed_file()

@app.route('/getfile/<filename>')
def get_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],filename)
# end of get_file()


@app.route('/splicesite', methods=['GET','POST'])
def splice_site():
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

        # Set up the mutation information for this run 
        session['chromosome'] = 'chr1'
        session['position'] = '1'
        session['base'] = 'A'
        if 'chromosome' in request.form and \
            request.form['chromosome'] != session['chromosome']:
            session['chromosome'] = request.form['chromosome']
        if 'position' in request.form and \
            request.form['position'] != session['position']:
            session['position'] = request.form['position']
        if 'base' in request.form and \
            request.form['base'] != session['base']:
            session['base'] = request.form['base']

        createSession()
        genomePath = "genomes"
        if session['db'] == 'hg19':
            genomeFile = "hg19.2bit"
        else:
            session['db'] = 'hg38'
            genomeFile = "hg38.2bit"
        genomeFilePath = "/".join([genomePath,genomeFile])

        #if app.config['GB'] == 'UCSC':
        #    seq = genomebrowser.gb_getSequence(hgsid, db=db, chrom=chrom,
        #                                       left=(int(pos)-1),
        #                                       right=(int(pos)),
        #                                       leftPad=500,
        #                                       rightPad=500)
        #else:    
        chrom = "chr%s"%(session['chromosome'])
        seqStart = int(session['position']) - 501
        seqEnd = int(session['position']) + 500
        genome = sequenceutils.loadGenome(genomeFilePath)
        seq = sequenceutils.getSequence(genome, chrom, seqStart, seqEnd)

        # make a copy of seq but with the base modified at specified position
        # python doesn't support item assignments w/in strings so build pieces
        var = seq[0:500]
        var = var + session['base']
        var = var + seq[501:]

        expectedSites = fruitfly.getSpliceSitePredictions(seq)
        variantSites = fruitfly.getSpliceSitePredictions(var)

        expectedList = []
        variantList = []
        msgList = []

        for ss in expectedSites:
            expectedList.append([ss.start,
                                 ss.end,
                                 ss.score,
                                 ss.intron,
                                 ss.exon])

        for ss in variantSites:
            variantList.append([ss.start,
                                ss.end,
                                ss.score,
                                ss.intron,
                                ss.exon])

        # List where we will store the SpliceSites to print
        # These are the sites that are "interesting"
        reportList = []

        for i, variantSite in enumerate(variantSites):
            (posB,baseB,scoreB) = variantSite.getSpliceSite()
            foundMatch = False
            for j, expectedSite in enumerate(expectedSites):
                (posA,baseA,scoreA) = expectedSite.getSpliceSite()
                if posA==posB:
                    foundMatch = True
                    if scoreA==scoreB:
                        if baseA != baseB:
                            flash("Base changed from %s to %s at position %d "
                                "with score %0.2f\n"%(baseA, baseB, posA, scoreA))
                    else:
                        delta = abs(scoreA - scoreB)
                        if delta >= 0.4:
                            flash("Score changed by %0.2f from %0.2f to %0.2f "
                                "at position %d.\n"%(delta, scoreA, scoreB, posA))
            if not foundMatch:

                if posB >= len(seq):
                    flash("Oops! Somehow the length of our expected and varied "
                        "sequences is not equivalent (%d for expected, "
                        "%d for varied).\n"%(len(seq),len(var)))
                    break
                origBase = seq[posB].lower()

                msgList.append("New splice site predicted at position %d with score %0.2f. "
                    "Original base was '%s' and new base is '%s'."
                    %(posB, scoreB, origBase, baseB))

                reportList.append([variantSite.start,
                                   variantSite.end,
                                   variantSite.score,
                                   variantSite.intron,
                                   variantSite.exon])
                

        return render_template('splicesite.html',
                               expectedList=expectedList,
                               variantList=variantList,
                               msgList=msgList,
                               reportList=reportList,
                               db=session['db'],
                               chromosome=session['chromosome'],
                               position=session['position'],
                               base=session['base'])

    # if not post, return index.html
    return render_template('index.html')

# end of splice_site()

@app.route('/multiplesites', methods=['GET','POST'])
def multiple_sites():
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
        session['chromcol'] = '#CHROM'
        session['poscol'] = 'POS'
        session['varcol'] = 'VARIANT'
        if 'chromcol' in request.form and \
            request.form['chromcol'] != session['chromcol']:
            session['chromcol'] = request.form['chromcol']
            flash("Using %s as chromosome column name"%(session['chromcol']))
        if 'poscol' in request.form and \
            request.form['poscol'] != session['poscol']:
            session['poscol'] = request.form['poscol']
            flash("Using %s as position column name"%(session['poscol']))
        if 'varcol' in request.form and \
            request.form['varcol'] != session['varcol']:
            session['varcol'] = request.form['varcol']
            flash("Using %s as variant column name"%(session['varcol']))
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
            #predictSpliceSites(session['uuid'],
            #                   rows,
            #                   genomeFilePath,
            #                   db=session['db'],
            #                   chromcol=session['chromcol'],
            #                   poscol=session['poscol'],
            #                   varcol=session['varcol'],
            #                  )
            #return render_template('predictionstatus.html')

            pr_args = [rows,
                       genomeFilePath,
                       session['db'],
                       session['chromcol'],
                       session['poscol'],
                       session['varcol'],
                      ] 

            task = predictSpliceSites.apply_async(args=pr_args)
            logger.info('Created task with id %s'%(task.id))
            return render_template('status.html', myfunc='predictions', task_id=task.id)

    return render_template('index.html')

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

            pr_args = [rows,
                       genomeFilePath,
                       session['db'],
                       session['chromcol'],
                       session['poscol'],
                       session['refcol'],
                       session['bracketlen'],
                       session['primerlen'],
                      ] 

            task = processRows.apply_async(args=pr_args)
            logger.info('Created task with id %s'%(task.id))
            return render_template('status.html', myfunc='primers', task_id=task.id)
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
