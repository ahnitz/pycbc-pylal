#!/usr/bin/python

import matplotlib
matplotlib.use("Agg")
from matplotlib import figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numarray

from glue import segments
from pylal import rate

import webplot


#
# Trigger rate vs. frequency plot description
#

class Plot(webplot.PlotDescription):
	pass


#
# How to make a trigger rate vs. frequency plot
#

def makeplot(desc, table):
	duration = float(segments.segmentlist.duration(desc.seglist & segments.segmentlist([desc.segment])))
	
	fig = figure.Figure()
	canvas = FigureCanvasAgg(fig)
	fig.set_figsize_inches(16,8)
	axes = fig.gca()

	xvals, yvals = rate.smooth(table.getColumnByName("central_freq").asarray(), desc.band, desc.freqwidth)
	axes.plot(xvals, yvals / duration)

	axes.set_xlim(list(desc.band))
	axes.set_xticks(numarray.arange(desc.band[0], desc.band[1], 100))
	axes.grid(True)

	axes.set_title(desc.instrument + " Excess Power Trigger Rate vs. Central Frequency\n(GPS Times %s ... %s, %d Triggers, %g Hz Average)" % (desc.segment[0], desc.segment[1], len(table), desc.freqwidth))
	axes.set_xlabel("Central Frequency (Hz)")
	axes.set_ylabel("Rate Density (Triggers/s per Hz)")

	fig.savefig(desc.filename)


#
# Make a plot and send to client
#

description = Plot().parse_form()

makeplot(description, webplot.gettriggers(description)[0])

webplot.SendImage(description)
