""" Main module for the ConfigObj version of the EPAR task editor

$Id$
"""

import os, tkMessageBox
import cfgpars, editpar, filedlg


# Starts a GUI session
def epar(theTask, parent=None, isChild=0):

    dlg = ConfigObjEparDialog(theTask, parent, isChild)
    return dlg.getTaskParsObj()


# Main class
class ConfigObjEparDialog(editpar.EditParDialog):

    def __init__(self, theTask, parent=None, isChild=0,
                 title="Config Parameter Editor", childList=None):

        # Init base - calls _setTaskParsObj(), sets self.taskName, etc
        editpar.EditParDialog.__init__(self, theTask, parent, isChild,
                                       title, childList, resourceDir='')

    # Always allow the Open button ?
    def _showOpenButton(self): return True


    # Employ an edited callback for a given item?
    def _defineEditedCallbackObjectFor(self, parScope, parName):
        """ Override to allow us to use an edited callback. """

        # We know that the _taskParsObj is a ConfigObjPars
        triggerStr = self._taskParsObj.getTriggerStr(parScope, parName)

        # Some items will have a trigger, but likely most won't
        if triggerStr:
            return self
        else:
            return None


    def edited(self, scope, name, lastSavedVal, newVal):
        """ This is the callback function invoked when an item is edited.
            This is only called for those items which were previously
            specified to use this mechanism.  We do not turn this on for
            all items because the performance might be prohibitive. """
        # the print line is a stand-in
        triggerStr = self._taskParsObj.getTriggerStr(scope, name)
        print scope+"."+name+", on disk: "+lastSavedVal+", now: "+newVal
#             ", trigger: "+triggerStr
    

    # a main function
    def _setTaskParsObj(self, theTask):
        """ Overridden version for ConfigObj. theTask can be either
            a .cfg file name or a ConfigObjPars object. """

        if isinstance(theTask, cfgpars.ConfigObjPars):
            self._taskParsObj = theTask

        elif os.path.isfile(str(theTask)):
            self._taskParsObj=cfgpars.ConfigObjPars(theTask,forUseWithEpar=True)

        else: # it must be a package name to load
            self._taskParsObj = cfgpars.findObjFor(theTask,forUseWithEpar=True)


    def _getSaveAsFilter(self):
        """ Return a string to be used as the filter arg to the save file
            dialog during Save-As. """
        filt = '*.cfg'
        if 'UPARM_AUX' in os.environ:
            upx = os.environ['UPARM_AUX']
            if len(upx) > 0:  filt = upx+"/*.cfg" 
        return filt


    def runTask(self):
        """ Override the base class version so that we can exit the Tkinter
            loop, since in this stand-alone version of the parameter editor
            we were spawned from the command line (no background CLI). """
        # If destroy() is not called, the symptom would be that GUI tasks,
        # when finished executing, would leave the process in a hung-like state
        try:
            from Tkinter import  _default_root
            if _default_root: _default_root.destroy()
        except:
            pass
        # Now simply defer to base class
        editpar.EditParDialog.runTask(self)


    # OPEN: load parameter settings from a user-specified file
    def pfopen(self, event=None):
        """ Load the parameter settings from a user-specified file. """

        # could use Tkinter's FileDialog, but this one is prettier
        fd = filedlg.PersistLoadFileDialog(self.top, "Load Config File",
                                           self._getSaveAsFilter())
        if fd.Show() != 1:
            fd.DialogCleanup()
            return
        fname = fd.GetFileName()
        fd.DialogCleanup()
        if fname == None: return

        # Now load it: "Loading "+self.taskName+" param values from: "+fname
        print "Loading "+self.taskName+" param values from: "+fname
        tmpObj = cfgpars.ConfigObjPars(fname, forUseWithEpar=True)

        # check it to make sure it is a match
# !     if self._taskParsObj.isSameTaskAs(tmpObj): ...

        # Set the GUI entries to these values (let the user Save after)
        newParList = tmpObj.getParList()
        try:
            self.setAllEntriesFromParList(newParList)
        except editpar.UnfoundParamError, pe:
            tkMessageBox.showwarning(message=pe.message, title="Error in "+\
                                     os.path.basename(fname))


    def unlearn(self, event=None):
        """ Override this so that we can set to deafult values our way. """
        self._setToDefaults()

    def _setToDefaults(self):
        """ Load the default parameter settings into the GUI. """

        # Now load it: "Loading "+self.taskName+" param values from: "+fname
        print "Loading default "+self.taskName+" param values"

        # Create an empty onject, where every item will be set to it's default
        # value
        try:
            tmpObj = cfgpars.ConfigObjPars(self.taskName+'.cfg',
                                           setAllToDefaults=True,
                                           forUseWithEpar=True)
        except Exception, ex:
            msg = "Error Creating Default Object"
            tkMessageBox.showerror(message=msg+'\n\n'+ex.message,
                                   title="Error Creating Default Object")
            return

        # Set the GUI entries to these values (let the user Save after)
        newParList = tmpObj.getParList()
        try:
            self.setAllEntriesFromParList(newParList)
        except editpar.UnfoundParamError, pe:
            tkMessageBox.showerror(message=pe.message,
                                   title="Error Setting to Default Values")