from __future__ import division # confidence high

import sys

pkg = "nictools"

setupargs = {
    'version' : 		"1.0.1",
    'description' : 	"Python Tools for NICMOS Data",
    'author' : 		"Vicki Laidler, David Grumm",
    'author_email' : 	"help@stsci.edu",
    'license' : 		"http://www.stsci.edu/resources/software_hardware/pyraf/LICENSE",
    'platforms' : 	["Linux","Solaris","Mac OS X"],
    'package_dir' : { 'nictools' : 'lib/nictools' },
    'data_files' : 	[('nictools',['SP_LICENSE'])],
    }
