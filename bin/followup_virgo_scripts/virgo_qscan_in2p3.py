#!/usr/bin/env python
"""
$Id$

Manager program to run specific parts of the followup on the CCIN2P3 cluster
"""

__author__ = 'Damir Buskulic <buskulic@lapp.in2p3.fr>'
__date__ = '$Date$'
__version__ = '$Revision$'[11:-2]

##############################################################################
# import standard modules and append the lalapps prefix to the python path
import sys, os, copy, math, random
import socket, time
import re, string
from optparse import *
import tempfile
import ConfigParser
import urlparse
import urllib
from UserDict import UserDict
#sys.path.append('/archive/home/buskulic/opt/s5_1yr_followup_20080131/lalapps/lib/python2.4/site-packages/lalapps')

##############################################################################
#
#  MAIN PROGRAM
#
##############################################################################

######################## OPTION PARSING  #####################################
usage = """
usage: %prog [options]
"""
parser = OptionParser( usage )

parser.add_option("-v", "--version",action="store_true",default=False,\
    help="print version information and exit")
parser.add_option("-o", "--output-directory",action="store",type="string",\
    help="output result directory")
parser.add_option("-T", "--times-file-scan",action="store",type="string",\
    help="file containing a list of times")
parser.add_option("-t", "--times-file-scanlite",action="store",type="string",\
    help="file containing a list of times")
parser.add_option("-S", "--configuration-file-scan",action="store",type="string",\
    help="configuration file for the scan process")
parser.add_option("-s", "--configuration-file-scan-seismic",action="store",type="string",\
    help="configuration file for the seismic scan process")
parser.add_option("-L", "--configuration-file-scanlite",action="store",type="string",\
    help="configuration file for the scanlite process")
parser.add_option("-l", "--configuration-file-scanlite-seismic",action="store",type="string",\
    help="configuration file for the seismic scanlite process")

command_line = sys.argv[1:]
(opts,args) = parser.parse_args()

if opts.version:
  print "$Id$"
  sys.exit(0)

#########  READING TIMES FILE AND LAUNCHING BATCH QSCANS SCRIPTS  ############

depIfoDir = './'
if not opts.times_file_scan:
   if os.path.exists(depIfoDir+'/TIMES/qscan_times.txt'):
      depQscanTFile =  open(depIfoDir+'/TIMES/qscan_times.txt','r')
else:
   depQscanTFile =  open(depIfoDir+'/'+opts.times_file_scan,'r')

if not opts.times_file_scanlite:
   if os.path.exists(depIfoDir+'/TIMES/background_qscan_times.txt'):
      depQscanLiteTFile =  open(depIfoDir+'/TIMES/background_qscan_times.txt','r')
else:
   depQscanLiteTFile =  open(depIfoDir+'/'+opts.times_file_scanlite,'r')

if not opts.output_directory:
   outputDir = 'RESULTS'
else:
   outputDir = opts.output_directory
print outputDir

if not opts.configuration_file_scan:
   depConfigScan = 'CONFIG/foreground-qscan_config.txt'
else:
   depConfigScan = opts.configuration_file_scan
print outputDir

if not opts.configuration_file_scan_seismic:
   depConfigSeismicScan = 'CONFIG/foreground-seismic-qscan_config.txt'
else:
   depConfigSeismicScan = opts.configuration_file_scan_seismic
print outputDir

if not opts.configuration_file_scanlite:
   depConfigScanLite = 'CONFIG/background-qscan_config.txt'
else:
   depConfigScanLite = opts.configuration_file_scanlite
print outputDir

if not opts.configuration_file_scanlite_seismic:
   depConfigSeismicScanLite = 'CONFIG/background-seismic-qscan_config.txt'
else:
   depConfigSeismicScanLite = opts.configuration_file_scanlite_seismic
print outputDir

if os.path.exists(depIfoDir+'/TIMES/qscan_times.txt'):
   print '***'
   print '*** Foreground qscans'
   print '***'
   qscanLines = depQscanTFile.readlines()
   for qscanTimeRaw in qscanLines:
      qscanTime = qscanTimeRaw.rstrip('\n')
      print 'Launching foreground qscan for time '+qscanTime
      qscanCommand = './SCRIPTS/qsub_wscan.sh '+qscanTime+' '+depConfigScan+' '+outputDir+'/results_foreground-qscan @foreground@'
      print '      command : '+qscanCommand
      os.system(qscanCommand)
      qscanCommand = './SCRIPTS/qsub_wscan.sh '+qscanTime+' '+depConfigSeismicScan+' '+outputDir+'/results_foreground-seismic-qscan @foreground-seismic@'
      print '      command : '+qscanCommand
      os.system(qscanCommand)

if os.path.exists(depIfoDir+'/TIMES/background_qscan_times.txt'):
   print '***'
   print '*** Background qscans (qscanlite)'
   print '***'
   qscanLines = depQscanLiteTFile.readlines()
   for qscanTimeRaw in qscanLines:
      qscanTime = qscanTimeRaw.rstrip('\n')
      print 'Launching background qscan (qscanlite) for time '+qscanTime
      qscanCommand = './SCRIPTS/qsub_wscanlite.sh '+qscanTime+' '+depConfigScanLite+' '+outputDir+'/results_background-qscan'
      print '      command : '+qscanCommand
      os.system(qscanCommand)
      qscanCommand = './SCRIPTS/qsub_wscanlite.sh '+qscanTime+' '+depConfigSeismicScanLite+' '+outputDir+'/results_background-seismic-qscan'
      print '      command : '+qscanCommand
      os.system(qscanCommand)

##########################################################################
sys.exit(0)
