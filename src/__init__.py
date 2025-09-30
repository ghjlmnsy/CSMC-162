"""
Mini Image Editor - Source Package

Modular image viewer/editor with PCX file format support.
"""

__version__ = "2.0.0"
__authors__ = "Salcedo, Chris Samuel (2022-05055) & Suyman, Ann Junah (2022-09089)"

from .main_app import ImageViewerApp
from .utils import ImageHistory, ColorUtils
from .image_tools import ImageTools
from .ui_components import ToolTip
from .pcx_reader import PCXReader, PCXHeader
from .pcx_info_window import PCXInfoWindow

__all__ = [
    'ImageViewerApp',
    'ImageHistory',
    'ColorUtils',
    'ImageTools',
    'ToolTip',
    'PCXReader',
    'PCXHeader',
    'PCXInfoWindow',
]
