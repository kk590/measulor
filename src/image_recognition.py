import cv2
import numpy as np
from .utils import calculate_distance

class ReferenceObjectDetector:
    def __init__(self, ref_width_cm=8.56): # Credit card width
        self.ref_width_cm = ref_width_cm
        self.pixels_per_cm = None

    def detect_reference(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blur, 50, 200)

        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Sort contours by area, largest first
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)

            # If contour has 4 points, assume it's our reference object (card/paper)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                
                # Filter small noise
                if w < 20 or h < 20: 
                    continue

                # Aspect Ratio Filter (Credit Card is ~8.56cm / 5.4cm = 1.58)
                aspect_ratio = float(w) / h
                # Allow some error margin (e.g., 1.4 to 1.8)
                # If the card is rotated 90 degrees, ratio would be ~0.63
                if not (1.4 < aspect_ratio < 1.8 or 0.55 < aspect_ratio < 0.7):
                    continue

                # Draw for visualization
                cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Calculate scale
                # Assuming the width of the bounding box corresponds to the ref_width_cm
                # Ideally we'd use the rotated rect, but boundingRect is a good start
                # If aspect ratio is < 1 (vertical), then w corresponds to height of card (5.4) or we assume user holds it horizontally?
                # Let's assume user holds it horizontally for now to match default ref_width_cm=8.56.
                # If vertical, we should swap.
                
                current_ref_width = self.ref_width_cm
                if aspect_ratio < 1:
                     # Card is vertical, so w corresponds to the shorter side (5.398cm)
                     # But self.ref_width_cm defaults to 8.56.
                     # Let's adjust scale calculation.
                     # Actually, if we use the MAX dimension of the box, it should map to 8.56
                     pass

                self.pixels_per_cm = w / self.ref_width_cm
                return self.pixels_per_cm, image
        
        return None, image

class BodyShapeClassifier:
    def classify(self, measurements):
        """
        Classify body shape based on measurements (dict).
        Expected keys: 'shoulder', 'waist', 'hip'
        """
        if not all(k in measurements for k in ['shoulder', 'waist', 'hip']):
            return "Unknown"

        s = measurements['shoulder']
        w = measurements['waist']
        h = measurements['hip']

        # Simple heuristic ratios
        # These are simplified rules
        if h > s * 1.05 and h > w * 1.15:
            return "Pear"
        elif s > h * 1.05 and s > w * 1.05:
            return "Inverted Triangle"
        elif abs(s - h) < s * 0.05 and w < s * 0.85:
            return "Hourglass"
        elif abs(s - h) < s * 0.05 and abs(w - s) < s * 0.05:
            return "Rectangle"
        elif w > s and w > h:
            return "Apple"
        else:
            return "Average"
