#### ReTrieve Figure Format ####
# 
# Description
# - Defines formatting for ReTrieve figures
#
# Usage
# - Use when creating a ReTrieve figure
# 
# Project: ReTrieve
# Author: Rachael Affenit Hudson
# Created: 03-27-2020
# Updated: 03-31-2020

from RePlayAnalysisCore3.Activities.ReTrieveAnalysisCore import rtvPalette
import numpy as np
import seaborn as sns
import matplotlib.ticker as ticker

FIG_SIZE_SINGLE_BAR = (2,4)
FIG_SIZE_SQUARE_SMALL = (4,3)
FIG_SIZE_SQUARE_MED = (6,6)
FIG_SIZE_WIDE = (12,4)
FIG_SIZE_RECT = (6,3)
FIG_SIZE_LARGE_TALL = (8,13)
FIG_SIZE_LARGE_WIDE = (12,6)

TITLE_FONT_SIZE = 17
MAIN_FONT_SIZE = 15
SMALL_FONT_SIZE = 14

def formatSubplot(plot, axis=None, title=None, xTickLabels=None, tickLabelRotation=None, xLabel=None, yLabel=None, ylim=None, gridlines=None, legend="visible"):
    
    if gridlines is not None:
        if gridlines:
            sns.set_style("whitegrid")
    else:
        sns.set_style(rtvPalette.background)
        sns.set(style="ticks", rc={"lines.linewidth": 1.5})

    # TODO: Figure out how to edit the number of y-axis ticks/gridlines
    # if axis is not None:
    #     axis.yaxis.set_major_locator(ticker.MultipleLocator(5))
    #     axis.yaxis.set_major_formatter(ticker.ScalarFormatter())
        
    sns.despine()

    if title is not None:
        plot.set_title(label=title, fontdict=dict(fontsize=TITLE_FONT_SIZE, fontweight="bold"), loc="center")

    if tickLabelRotation is not None: 
        plot.tick_params(labelsize=MAIN_FONT_SIZE, labelrotation=tickLabelRotation)
    else:
        plot.tick_params(labelsize=MAIN_FONT_SIZE)
    
    if xTickLabels is not None: 
        plot.set_xticklabels(xTickLabels)
    
    if yLabel is not None:
        plot.set_ylabel(yLabel, fontsize = MAIN_FONT_SIZE)
    
    if xLabel is None:
        plot.set_xlabel("")
    else:
        plot.set_xlabel(xLabel, fontsize = MAIN_FONT_SIZE)

    if legend is "invisible":
        plot.legend().remove()
        
    elif legend is "swarm":
        handles, labels = plot.get_legend_handles_labels()
        halfLen = int(len(handles)/2)
        plot.legend(
            handles=list(handles[halfLen:]), 
            labels=list(labels[halfLen:]),
            frameon=False, 
            prop=dict(size=SMALL_FONT_SIZE),
            bbox_to_anchor=(0.5, -0.1), 
            loc="upper center",
            ncol=len(handles),
        )
    elif legend is "bar":
        handles, labels = plot.get_legend_handles_labels()
        plot.legend(
            frameon=False, 
            prop=dict(size=SMALL_FONT_SIZE),
            bbox_to_anchor=(0.5, -0.1), 
            loc="upper center",
            ncol=len(handles),
        )
    else:
        plot.legend( 
            prop=dict(size=SMALL_FONT_SIZE),
        )

    if ylim is not None and ylim is not np.nan:
        plot.set(ylim=(0, ylim))
    else:
        plot.set_ylim(bottom=0)
    
    return plot

def formatFigure(fig, refSubplot=None, title=None, legend=None):
    fig.subplots_adjust(top=0.9)
    if title is not None:
        fig.suptitle(
            title, 
            fontsize=TITLE_FONT_SIZE,
            fontweight="bold",
            y=1.04
        )
    if legend is "invisible":
        fig.legend().remove()
        
    elif legend is "swarm" and refSubplot is not None:
        handles, labels = refSubplot.get_legend_handles_labels()
        halfLen = int(len(handles)/2)
        fig.legend(
            handles=list(handles[halfLen:]), 
            labels=list(labels[halfLen:]),
            loc="lower center",
        )
    elif legend is "bar" and refSubplot is not None:
        handles, labels = refSubplot.get_legend_handles_labels()
        fig.legend(
            handles= handles,
            labels= labels,
            loc="lower center",
        )
    fig.tight_layout(pad=0.5)
    return fig

# Define figure formatting
titleFont = {
    'fontsize': TITLE_FONT_SIZE,
    'fontweight' : "bold"
}

legendFont = {
    'size': SMALL_FONT_SIZE
}

tickLabelFont = {
    'size': SMALL_FONT_SIZE
}

axisLabelFont = {
    'size': 15
}

if __name__ == "__main__":
    import doctest
    doctest.testmod()