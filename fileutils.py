"""File utilities for the pyprimer3 Flask app.

Handles reading CSV and Excel files into dictionaries.
Includes a routine to write Primer data to CSV.
"""

import csv
import xlrd

from pclass import Primer

__author__ = "Joe Carli"
__copyright__ = "Copyright 2014"
__credits__ = ["Joe Carli"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Joe Carli"
__email__ = "jrcarli@gmail.com"
__status__ = "Development"

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
    print "Writing %d primers to %s"%(len(primerList),outfile)
    with open(outfile,'wb') as f:
        f.write('Name%cSequence%cSize\n'%(delim,delim))
        for primer in primerList:
            output = str(primer)
            f.write(output+'\n')
# end of primersToCsv()        

def predictionsToCsv(predictionList,outfile,delim=','):
    with open(outfile,'wb') as f:
        f.write('Start%cEnd%cScore%cIntron%cExon\n'%(delim,delim,delim,delim))
        # each element in predictionList is a SpliceSite
        for prediction in predictionList:
            output = str(prediction) 
            #output = ('%d%c%d%c%0.2f%c%s%c%s'%(start,delim,
            #                                   end,delim,
            #                                   score,delim,
            #                                   intron,delim,
            #                                   exon))
            f.write(output+'\n')
# end of predictionsToCsv()
