#!/usr/bin/env python
"""
A library of utility functions

"""
from __future__ import division # confidence medium

import numpy as np
import pyfits
from pytools import asnutil,fileutil
from pytools import teal
import os
import logging,traceback
import sys

__version__ = "0.1.0tng1"
__pyfits_version__ = pyfits.__version__
__numpy_version__ = np.__version__

"""
Logging routines
"""
class StreamLogger(object):
    """ Class to manage trapping of STDOUT and STDERR messages to a trailer file
    """

    def __init__(self, stream, logfile, mode='w', prefix=''):
        self.stream = stream
        if prefix in [None,'',' ']:
            self.prefix = ''
        else:
            self.prefix = '['+prefix+'] '
        self.data = ''
        
        # set up logfile
        if logfile not in [None,"None","INDEF",""," "]:
            self.log = open(logfile,mode)
            self.filename = logfile
            # clear out any previous exceptions, so that only those generated
            # by this code will be picked up in the trailer file
            sys.exc_clear()
            print '[betadrizzle] Trailer file will be written out to: ',self.filename
        else:
            self.log = None
            self.filename = None
            print '[betadrizzle] No trailer file will be created...'

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()

        if self.log is not None:
            self.data += data
            tmp = str(self.data)
            if '\x0a' in tmp or '\x0d' in tmp:
                tmp = tmp.rstrip('\x0a\x0d')
                self.log.write('%s%s\n' % (self.prefix,tmp))
                self.data = ''
            
def init_logging(logfile='betadrizzle.log'):    
    """ Set up logfile for capturing stdout/stderr messages.
        Must be called prior to writing any messages that you want to log.
    """

    if logfile not in [None,""," ","INDEF"]:
        if '.log' in logfile:
            logname = logfile
        else:
            logname = logfile+'.log'
    else:
        logname = None
    # redirect logging of stdout to logfile
    sys.stdout = StreamLogger(sys.stdout, logname)

def end_logging():
    """ Close log file and restore stdout/stderr to system defaults.
    """
    if sys.stdout.log is not None:
        print '[betadrizzle] Trailer file written to: ',sys.stdout.filename
        sys.stdout.log.flush()
        sys.stdout.log.close()

        # Add any traceback information to the trailer file to document
        # the error that caused the code to stop processing
        if sys.exc_info()[0] is not None:
            errfile = open(sys.stdout.filename,mode="a")
            traceback.print_exc(None,errfile)
            errfile.close()
    else:
        print '[betadrizzle] No trailer file saved...'
    
    sys.stdout = sys.__stdout__
    
class ProcSteps:
    """ This class allows MultiDrizzle to keep track of the 
        start and end times of each processing step that gets run
        as well as computing/reporting the elapsed time for each step.
        
        The code for each processing step must call the 'addStep()' 
        method to initialize the information for that step, then
        the 'endStep()' method to record the end and elapsed times.
        
        The 'reportTimes()' method can then be used to provide a summary
        of all the elapsed times and total run time. 
    """
    __report_header = '\n   %20s          %s\n'%('-'*20,'-'*20)
    __report_header += '   %20s          %s\n'%('Step','Elapsed time')
    __report_header += '   %20s          %s\n'%('-'*20,'-'*20)

    def __init__(self):
        self.steps = {}
        self.order = []
        self.start = _ptime()
        self.end = None

    def addStep(self,key):
        """ 
        Add information about a new step to the dict of steps
        The value 'ptime' is the output from '_ptime()' containing
        both the formatted and unformatted time for the start of the 
        step
        """
        ptime = _ptime()
        print '==== Processing Step ',key,' started at ',ptime[0]
        self.steps[key] = {'start':ptime}
        self.order.append(key)

    def endStep(self,key):
        """ 
        Record the end time for the step.
        
        If key==None, simply record ptime as end time for class to represent
        the overall runtime since the initialization of the class.
        """
        ptime = _ptime()
        if key is not None:
            self.steps[key]['end'] = ptime
            self.steps[key]['elapsed'] = ptime[1] - self.steps[key]['start'][1]
        self.end = ptime
        
        print'==== Processing Step ',key,' finished at ',ptime[0]
    
    def reportTimes(self):
        """ Print out a formatted summary of the elapsed times for all 
            the performed steps
        """
        self.end = _ptime()
        total_time = 0
        print ProcSteps.__report_header 
        for step in self.order:
            if self.steps[step].has_key('elapsed'):
                _time = self.steps[step]['elapsed']
            else: 
                _time = 0.0
            total_time += _time
            print '   %20s          %0.4f sec.'%(step,_time)

        print '   %20s          %s'%('='*20,'='*20)
        print '   %20s          %0.4f sec.'%('Total',total_time)
        
        # Compute overall runtime of entire program, including overhead
        #total = self.end[1] - self.start[1]
        #print '   %20s          %0.4f sec.'%('Total Runtime',total)

def _ptime():
    import time
    try:
        import datetime as dtime
    except ImportError:
        dtime = None
    ftime = time.time()
    if dtime:
        # This time stamp includes sub-second timing...
        _ltime = dtime.datetime.fromtimestamp(ftime)
        tlm_str = _ltime.strftime("%H:%M:%S")+str(_ltime.microsecond/1e+6)[1:-3]+_ltime.strftime(" (%d/%m/%Y)")
    else:
        # Basic time stamp which only includes integer seconds
        # Format time values for keywords IRAF-TLM, and DATE
        _ltime = time.localtime(ftime)
        tlm_str = time.strftime('%H:%M:%S (%d/%m/%Y)',_ltime)
        #date_str = time.strftime('%Y-%m-%dT%H:%M:%S',_ltime)
    return tlm_str,ftime
    
def findrootname(filename):
    """
    return the rootname of the given file
    """

    puncloc = [filename.find(char) for char in string.punctuation]
    val = sys.maxint
    for num in puncloc:
        if num !=-1 and num < val:
            val = num
    return filename[0:val]

def removeFileSafely(filename,clobber=True):
    """ Delete the file specified, but only if it exists and clobber is True
    """ 
    if filename is not None and filename.strip() != '':
        if os.path.exists(filename) and clobber: os.remove(filename)
    
def getDefaultConfigObj(taskname,configObj,input_dict={},loadOnly=True):
    """ Return default configObj instance for task updated 
        with user-specified values from input_dict.
        
        If configObj already defined, it will simply 
        return configObj unchanged. 
    """    
    if configObj is None:
        # Start by grabbing the default values without using the GUI
        # This insures that all subsequent use of the configObj includes
        # all parameters and their last saved values
        configObj = teal.teal(taskname,loadOnly=True)
        
        # merge in the user values for this run
        # this, though, does not save the results for use later
        if input_dict not in [None,{}] and configObj not in [None, {}]:
            mergeConfigObj(configObj,input_dict)
            # Update the input .cfg file with the updated parameter values 
            configObj.write()
            
        if not loadOnly: 
        # We want to run the GUI AFTER merging in any parameters 
        # specified by the user on the command-line and provided in 
        # input_dict
            configObj = teal.teal(configObj,loadOnly=False)
    
    return configObj
                    
def mergeConfigObj(configObj,input_dict):
    for key in input_dict:
        setConfigObjPar(configObj,key,input_dict[key])

def getSectionName(configObj,stepnum):
    """ Return section label based on step number.
    """
    for key in configObj.keys():
        if key.find('STEP '+str(stepnum)) >= 0:
            return key

def getConfigObjPar(configObj,parname):
    """ Return parameter value without having to specify which section
        holds the parameter.
    """
    for key in configObj:
        if isinstance(configObj[key], dict):
            for par in configObj[key]:
                if par == parname:
                    return configObj[key][par]
        else:
            if key == parname:
                return configObj[key]
            
def setConfigObjPar(configObj,parname,parvalue):
    """ Sets a parameter's value without having to specify which section
        holds the parameter.
    """
    for key in configObj:
        if isinstance(configObj[key], dict):
            for par in configObj[key]:
                if par == parname:
                    configObj[key][par] = parvalue
        else:
            if key == parname:
                configObj[key] = parvalue



"""
These two functions are for reading in an 'at file' which contains
two columns of filenames, the first column is assumed to
be the science image and the second column is assumed
to be the IVM file that is associated with it
"""

def atfile_sci(filename):
    """
    return the filename of the science image 
    which is assumed to be the first word
    in the atfile the user gave
    """
    return filename.split()[0]

    
def atfile_ivm(filename):
    """
    return the filename of the IVM file
    which is assumed to be the second word
    in the atfile the user gave
    """
    return filename.split()[1]    
    
    
def printParams(paramDictionary):
    """ Print nicely the parameters from the dictionary
    """

    if (len(paramDictionary) == 0):
        print "\nNo parameters were supplied\n"
    else:
        keys=paramDictionary.keys()
        keys.sort()
        for key in keys:
            print key,":\t",paramDictionary[key]


def isASNTable(inputFilelist):
    """return TRUE if inputFilelist is a fits ASN file"""
    if ("_asn"  or "_asc") in inputFilelist:
        return True
    return False

def isCommaList(inputFilelist):
    """return True if the input is a comma separated list of names"""
    if "," in inputFilelist:
        return True
    return False        
  
def loadFileList(inputFilelist):
    """open up the '@ file' and read in the science and possible
      ivm filenames from the first two columns
    """
    f = open(inputFilelist[1:])
    # check the first line in order to determine whether
    # IVM files have been specified in a second column...
    lines = f.readline()
    f.close()
    
    # If there is a second column...
    if len(line.split()) == 2:
        # ...parse out the names of the IVM files as well 
        ivmlist = irafglob.irafglob(input, atfile=atfile_ivm) 
    
    # Parse the @-file with irafglob to extract the input filename
    filelist = irafglob.irafglob(input, atfile=atfile_sci)
    return filelist


def readCommaList(fileList):
    """ return a list of the files with the commas removed """
    names=fileList.split(',')
    fileList=[]
    for item in names:
        fileList.append(item)
    return fileList
    


def getInputAsList(input, output=None, ivmlist=None, prodonly=False):
    if (isinstance(input, list) == False) and \
       ('_asn' in input or '_asc' in input) :
       
        # Input is an association table
        # Get the input files, and run makewcs on them
        oldasndict = asnutil.readASNTable(input, prodonly=prodonly)

        if not output:
            output = oldasndict['output']

        filelist = [fileutil.buildRootname(fname) for fname in oldasndict['order']]
        
    elif (isinstance(input, list) == False) and \
       (input[0] == '@') :
        # input is an @ file
        f = open(input[1:])
        # Read the first line in order to determine whether
        # IVM files have been specified in a second column...
        line = f.readline()
        f.close()
        # Parse the @-file with irafglob to extract the input filename
        filelist = irafglob.irafglob(input, atfile=atfile_sci)
        # If there is a second column...
        if len(line.split()) == 2:
            # ...parse out the names of the IVM files as well 
            ivmlist = irafglob.irafglob(input, atfile=atfile_ivm)        
    else:
        #input is a string or a python list
        try:
            filelist, output = parseinput.parseinput(input, outputname=output)
            #filelist.sort()
        except IOError: raise
        
    return filelist, output

def runmakewcs(input):
    """
    Runs 'updatewcs' to recompute the WCS keywords for the input image
    
    Parameters
    ----------
    input: list of str
        a list of file names

    Returns
    -------
    output: list of str 
        returns a list of names of the modified files
        (For GEIS files returns the translated names.)
    
    """
    newNames = updatewcs.updatewcs(input, checkfiles=False)
    
    return newNames


def update_input(filelist, ivmlist=None, removed_files=None):
    """
    Removes files flagged to be removed from the input filelist.
    Removes the corresponding ivm files if present.
    """
    newfilelist = []

    if removed_files == []:
        return filelist, ivmlist
    else:
        sci_ivm = zip(filelist, ivmlist)
        for f in removed_files:
            result=[sci_ivm.remove(t) for t in sci_ivm if t[0] == f ]
        ivmlist = [el[1] for el in sci_ivm] 
        newfilelist = [el[0] for el in sci_ivm] 
        return newfilelist, ivmlist 


####
#
# The following functions were required for use with the drizzling code
# and were copied in from pydrizzle_tng.py.
#
####

def countImages(imageObjectList):
    expnames = []
    for img in imageObjectList:
        expnames += img.getKeywordList('_expname')
    imgnames = []

    nimages = 0
    for e in expnames:
        if e not in imgnames:
            imgnames.append(e)
            nimages += 1
    return nimages

def get_detnum(hstwcs,filename,extnum):
    detnum = None
    binned = None
    if hstwcs.filename == filename and hstwcs.extver == extnum:
        detnum = hstwcs.chip
        binned = hstwcs.binned

    return detnum,binned

def get_expstart(header,primary_hdr):
    """shouldn't this just be defined in the instrument subclass of imageobject?"""

    if primary_hdr.has_key('expstart'):
        exphdr = primary_hdr
    else:
        exphdr = header
            
    if exphdr.has_key('EXPSTART'):
        expstart = float(exphdr['EXPSTART'])
        expend = float(exphdr['EXPEND'])
    else:
        expstart = 0.
        expend = 0.0

    return (expstart,expend)

def compute_texptime(imageObjectList):
    """
    Add up the exposure time for all the members in
    the pattern, since 'drizzle' doesn't have the necessary
    information to correctly set this itself.
    """
    expnames = []
    exptimes = []
    start = []
    end = []
    for img in imageObjectList:
        expnames += img.getKeywordList('_expname')
        exptimes += img.getKeywordList('_exptime')
        start += img.getKeywordList('_expstart')
        end += img.getKeywordList('_expend')
    
    exptime = 0.
    expstart = min(start)
    expend = max(end)
    exposure = None
    for n in range(len(expnames)):
        if expnames[n] != exposure:
            exposure = expnames[n]
            exptime += exptimes[n]

    return (exptime,expstart,expend)

def computeRange(corners):
    """ Determine the range spanned by an array of pixel positions. """
    _xrange = (np.minimum.reduce(corners[:,0]),np.maximum.reduce(corners[:,0]))
    _yrange = (np.minimum.reduce(corners[:,1]),np.maximum.reduce(corners[:,1]))
    return _xrange,_yrange

def getRotatedSize(corners,angle):
    """ Determine the size of a rotated (meta)image."""
    # If there is no rotation, simply return original values
    if angle == 0.:
        _corners = corners
    else:
        # Find center
        #_xr,_yr = computeRange(corners)
        #_cen = ( ((_xr[1] - _xr[0])/2.)+_xr[0],((_yr[1]-_yr[0])/2.)+_yr[0])
        _rotm = fileutil.buildRotMatrix(angle)
        # Rotate about the center
        #_corners = N.dot(corners - _cen,_rotm)
        _corners = np.dot(corners,_rotm)

    return computeRange(_corners)

def readcols(infile,cols=[0,1,2,3]):
    """ 
    Read the columns from an ASCII file as numpy arrays
    
    Parameters
    ----------
    infile: str
        filename of ASCII file with array data as columns
        
    cols: list of int
        list of 0-indexed column numbers for columns to be turned into numpy arrays
        (DEFAULT- [0,1,2,3])
        
    Returns
    -------
    outarr: list of numpy arrays
        simple list of numpy arrays in the order as specifed in the 'cols' parameter
        
    """

    fin = open(infile,'r')
    outarr = []
    for l in fin.readlines():
        l = l.strip()
        if len(l) == 0 or len(l.split()) < len(cols) or (len(l) > 0 and l[0] == '#' or (l.find("INDEF") > -1)): continue

        for i in range(10):
            lnew = l.replace("  "," ")
            if lnew == l: break
            else: l = lnew
            lspl = lnew.split(" ")

        if len(outarr) == 0:
            for c in range(len(cols)): outarr.append([])

        for c,n in zip(cols,range(len(cols))):
            outarr[n].append(float(lspl[c]))
    fin.close()
    for n in range(len(cols)):
        outarr[n] = np.array(outarr[n],np.float64)
    return outarr            

def createFile(dataArray=None, outfile=None, header=None):
    """Create a simple fits file for the given data array and header"""

    try:    
        assert(outfile != None), "Please supply an output filename for createFile"
        assert(dataArray != None), "Please supply a data array for createFiles"
    except AssertionError:
        raise AssertionError
    
    print 'Creating output : ',outfile

    try:
        # Create the output file
        fitsobj = pyfits.HDUList()
        if (header != None):
            del(header['NAXIS1'])
            del(header['NAXIS2'])
            if header.has_key('XTENSION'):
                del(header['XTENSION'])
            if header.has_key('EXTNAME'):
                del(header['EXTNAME'])
            if header.has_key('EXTVER'):
                del(header['EXTVER'])

            if header.has_key('NEXTEND'):
                header['NEXTEND'] = 0

            hdu = pyfits.PrimaryHDU(data=dataArray,header=header)
            del hdu.header['PCOUNT']
            del hdu.header['GCOUNT']

        else:
            hdu = pyfits.PrimaryHDU(data=dataArray)

        fitsobj.append(hdu)
        fitsobj.writeto(outfile)

    finally:
        # CLOSE THE IMAGE FILES
        fitsobj.close()
        del fitsobj  
