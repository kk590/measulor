import cv2
import numpy as np
import unittest
from src.image_recognition import ReferenceObjectDetector, BodyShapeClassifier
from src.measurement import MeasurementCalculator

class TestBodyMeasurement(unittest.TestCase):
    def test_reference_detection(self):
        # Create a dummy image (black background)
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        
        # Draw a white rectangle representing a credit card
        # Card ratio ~1.58. Let's make it 158x100 pixels.
        cv2.rectangle(img, (100, 100), (258, 200), (255, 255, 255), -1) 
        
        detector = ReferenceObjectDetector()
        px_per_cm, _ = detector.detect_reference(img)
        
        self.assertIsNotNone(px_per_cm, "Should detect the reference object")
        # Expected scale: 158 px / 8.56 cm = ~18.45
        expected_scale = 158 / 8.56
        self.assertAlmostEqual(px_per_cm, expected_scale, delta=1.0)
        print(f"Detected Scale: {px_per_cm:.2f} px/cm (Expected: {expected_scale:.2f})")

    def test_measurement_calculation(self):
        calc = MeasurementCalculator()
        # Set arbitrary calibration: 10 pixels = 1 cm
        calc.set_calibration(10.0)
        
        # Mock landmarks: [id, x, y, visibility]
        # Shoulder width 40cm -> 400px.
        # Hip width 30cm -> 300px.
        # 11: (100, 100), 12: (500, 100) -> Width 400px = 40cm
        # 23: (150, 600), 24: (450, 600) -> Width 300px = 30cm
        landmarks = [
            [11, 100, 100, 0.9], [12, 500, 100, 0.9],
            [23, 150, 600, 0.9], [24, 450, 600, 0.9]
        ]
        
        measurements = calc.calculate(landmarks)
        
        self.assertIn('shoulder', measurements)
        self.assertIn('hip', measurements)
        self.assertAlmostEqual(measurements['shoulder'], 40.0, delta=0.1)
        self.assertAlmostEqual(measurements['hip'], 30.0, delta=0.1)
        
        # Check waist estimation logic
        # Waist = 0.8 * (Shoulder + Hip) / 2 = 0.8 * (40+30)/2 = 0.8 * 35 = 28
        self.assertIn('waist', measurements)
        # Note: I changed the factor to 0.80 in previous step
        expected_waist = (40 + 30) / 2 * 0.80
        self.assertAlmostEqual(measurements['waist'], expected_waist, delta=0.1)
        print(f"Calculated Measurements: {measurements}")

if __name__ == '__main__':
    unittest.main()
