"""Top level entry of folioflex."""

# importing modules to be available at the package level namespace

from . import version
from .budget import budget, models
from .chatbot import providers
from .portfolio import broker, heatmap, portfolio, wrappers

__version__ = version.version
__author__ = "John Koestner"
