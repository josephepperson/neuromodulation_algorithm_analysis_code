#### ReTrieve Palette ####
# 
# Description
# - Colors and color palettes used in ReTrieve data analysis
#
# Usage
# - Reference color palettes in the "palette = <string>" argument of seaborn functions
# 
# Project: ReTrieve
# Author: Rachael Affenit Hudson
# Created: 09-05-2019
# Updated: 03-31-2020

from enum import Enum

# Define colors for color palettes
class Colors(Enum):
    RED = "#d93c21"
    YELLOW = "#e8ba2e"
    GREEN = "#32a852"
    BLUE = "#2b48ff"
    PURPLE = "#8f52a1"
    GREY = "#333333"
    BLACK = "black"
    WHITE = "white"
    TRANSPARENT = "#00FFFFFF"

# Color palettes to use for figures
Quad = [Colors.BLUE.value, Colors.RED.value, Colors.GREEN.value, Colors.GREY.value]
DiffColors = [Colors.GREEN.value, Colors.YELLOW.value, Colors.RED.value]
BlackSwarm = [Colors.BLACK.value, Colors.BLACK.value]
Triple = [Colors.BLUE.value, Colors.RED.value, Colors.GREEN.value]
TripleIndWithCtrl = [Colors.GREEN.value, Colors.BLUE.value, Colors.RED.value]
QuadIndWithGroup = [Colors.BLUE.value, Colors.RED.value, Colors.YELLOW.value, Colors.GREY.value]
QuadIndSwarm = [Colors.TRANSPARENT.value, Colors.TRANSPARENT.value, Colors.BLACK.value, Colors.BLACK.value]
Double = [Colors.BLUE.value, Colors.RED.value]
Random = [Colors.RED.value, Colors.GREY.value]
GreenYellow = [Colors.GREEN.value, Colors.YELLOW.value]
Green = [Colors.GREEN.value]
Impaired = [Colors.RED.value]
Control = [Colors.BLUE.value]
Grey = [Colors.GREY.value]
background = Colors.WHITE.value
