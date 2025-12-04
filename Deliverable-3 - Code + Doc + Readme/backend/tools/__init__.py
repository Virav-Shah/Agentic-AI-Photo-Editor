"""
Photo Editing Tools Module
Contains all CV and image processing tools for the photo editor.
"""

from .detect import detect_objects
from .seg import segment_object, segment_multiple_objects, segment_single_bbox, segment_with_detection
from .crop import crop_image
from .filter import apply_filter
from .resize import resize_image
from .parallax import create_parallax
from .sr import super_resolution
from .inpaint import inpaint_region
from .theme_changer import change_theme, get_available_weather_classes

__all__ = [
    'detect_objects',
    'segment_object',
    'segment_multiple_objects',
    'segment_single_bbox',
    'segment_with_detection',
    'crop_image',
    'apply_filter',
    'resize_image',
    'create_parallax',
    'super_resolution',
    'inpaint_region',
    'change_theme',
    'get_available_weather_classes'
]
