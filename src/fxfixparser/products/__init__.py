"""Product type handlers for FX instruments."""

from fxfixparser.products.base import ProductHandler
from fxfixparser.products.forward import ForwardHandler
from fxfixparser.products.futures import FuturesHandler
from fxfixparser.products.ndf import NDFHandler
from fxfixparser.products.options import OptionsHandler
from fxfixparser.products.spot import SpotHandler
from fxfixparser.products.swap import SwapHandler

__all__ = [
    "ProductHandler",
    "SpotHandler",
    "ForwardHandler",
    "SwapHandler",
    "NDFHandler",
    "FuturesHandler",
    "OptionsHandler",
]
