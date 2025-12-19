import math
import cv2
import numpy as np

def calculate_distance(p1, p2):
    """Calculate Euclidean distance between two points."""
    x1, y1 = p1
    x2, y2 = p2
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def resize_image(image, width=None, height=None):
    """Resize image maintaining aspect ratio."""
    (h, w) = image.shape[:2]
    if width is None and height is None:
        return image
    
    if width is None:
        r = height / float(h)
        dim = (int(w * r), height)
    else:
        r = width / float(w)
        dim = (width, int(h * r))
        
    return cv2.resize(image, dim, interpolation=cv2.INTER_AREA)
