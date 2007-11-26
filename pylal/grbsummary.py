from __future__ import division

import os
import re
import socket
import sys
import tempfile
import time
import urlparse
itertools = __import__("itertools")  # absolute import of system-wide itertools

from lalapps import inspiral

from glue import lal
from glue import pipeline
from glue import segments, segmentsUtils
from glue.ligolw import table
from glue.ligolw import lsctables
from glue.ligolw import utils

# from pylal import webCondor

##############################################################################
# Custom classes
##############################################################################

class GRBSummaryDAG(pipeline.CondorDAG):
  def __init__(self, config_file, log_path):
    self.basename = config_file.replace(".ini", "") 
    logfile, logfilename = tempfile.mkstemp(prefix=self.basename, suffix=".dag.log", dir=log_path)
    os.close(logfile)
    pipeline.CondorDAG.__init__(self, logfilename)
    self.set_dag_file(self.basename)

##############################################################################
# Utility functions
##############################################################################

def compute_masked_segments(analyzable_seglist, on_source_segment,
    veto_seglist=None, quantization_time=None):
    """
    Return veto segmentlists for on-source and off-source regions,
    respectively.  Optionally, use vetos from veto_seglist.  Optionally,
    quantize the off-source with quantization_time (seconds).
    """
    analyzable_seglist = segments.segmentlist(analyzable_seglist[:]).coalesce()
    if veto_seglist is None:
        veto_seglist = segments.segmentlist()
    off_source_segs = analyzable_seglist - segments.segmentlist([on_source_segment])

    ## on-source mask
    on_source_mask = off_source_segs | veto_seglist

    ## off-source mask
    # first, assign its value without quantization
    off_source_mask = segments.segmentlist([on_source_segment]) | veto_seglist

    # then, quantize as necessary
    if quantization_time is not None:
        off_source_quantized = segments.segmentlist(
            [segments.segment(s[0], s[0] + abs(s)//quantization_time) \
             for s in (off_source_segs - off_source_mask)])
        off_source_mask = analyzable_seglist - off_source_quantized

    return on_source_mask, off_source_mask

def compute_offsource_segment(analyzable, on_source, padding_time=0,
    max_trials=None, symmetric=True):
    """
    Compute and return the maximal off-source segment subject to the
    following constraints:
    
    1) The off-source segment is constrained to lie within a segment from the
       analyzable segment list and to contain the on_source segment.  If
       no such segment exists, return None.
    2) The off-source segment length is a multiple of the on-source segment
       length.  This multiple (minus one for the on-source segment) is called
       the number of trials.  By default, the number of trials is bounded
       only by the availability of analyzable time.

    Optionally:
    3) padding_time is subtracted from the analyzable segments, but added
       back to the off-source segment.  This represents time that is thrown
       away as part of the filtering process.
    4) max_trials caps the number of trials that the off-source segment
       can contain.  The truncation is performed so that the resulting
       off-source segment is as symmetric as possible.
    5) symmetric being True will simply truncate the off-source segment to
       be the symmetric about the on-source segment.
    """
    quantization_time = abs(on_source)
    
    try:
        super_seg = analyzable[analyzable.find(on_source)].contract(padding_time)
    except ValueError:
        return None
    
    # check again after taking padding into account
    if on_source not in super_seg:
        return None
    
    nplus = (super_seg[1] - on_source[1]) // quantization_time
    nminus = (on_source[0] - super_seg[0]) // quantization_time
    
    if (max_trials is not None) and (nplus + nminus > max_trials):
        half_max = max_trials // 2
        if nplus < half_max:
            # left sticks out, so cut it
            remainder = max_trials - nplus
            nminus = min(remainder, nminus)
        elif nminus < half_max:
            # right sticks out, so cut it
            remainder = max_trials - nminus
            nplus = min(remainder, nplus)
        else:
            # both sides stick out, so cut symmetrically
            nplus = nminus = half_max

    if symmetric:
        nplus = nminus = min(nplus, nminus)
    
    return segments.segment((on_source[0] - nminus*quantization_time - padding_time,
                             on_source[1] + nplus*quantization_time + padding_time))

def ext_trigger_gpstimes_from_xml(doc):
    """
    Return a dictionary of GPS times of external triggers keyed by the GRB
    name found in the ExtTriggersTables present in doc.  If there are no
    ExtTriggersTables in doc, return None.
    """
    ext_triggers_tables = lsctables.getTablesByType(doc, lsctables.ExtTriggersTable)
    if ext_triggers_tables is None:
        return None
    ext_triggers = {}
    for tab in ext_triggers_tables:
        for name, time in itertools.izip(tab.getColumnByName("event_number_grb"),
                                         tab.getColumnByName("start_time")):
            if name in ext_triggers:
                print >>sys.stderr, "warning: GRB %s appears twice in document; taking second definition"
            ext_triggers[name] = time
    return ext_triggers
    