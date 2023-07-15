# importing modules to be available at the package level namespace

from . import version
from .portfolio import portfolio

__version__ = version.version
__author__ = "John Koestner"
