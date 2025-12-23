from flask import Flask, request, jsonify
import cv2
import mediapipe as mp
import numpy as np
from PIL import Image
import io
import math

app = Flask(__name__)

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5)

def calculate_distance(point1, point2):
    """Calculate Euclidean distance between two points"""
    return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def estimate_pixels_per_cm(landmarks, image_height):
    """
    Estimate calibration using average human body proportions
    Average human height: 170 cm
    Head to toe distance in pixels can estimate total height
    """
    # Get nose (landmark 0) and ankle (landmark 27 or 28)
    if 0 in landmarks and 27 in landmarks:
        nose = landmarks[0]
        ankle = landmarks[27]
        pixel_height = abs(nose[1] - ankle[1])
        # Assume average height of 170 cm
        assumed_height_cm = 170
        pixels_per_cm = pixel_height / assumed_height_cm
        return pixels_per_cm
    return None

def process_image_measurements(image_data):
    """Process image and return measurements"""
    try:
        # Convert PIL Image to OpenCV format
        image_np = np.array(image_data)
        image_rgb = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)
        height, width, _ = image_rgb.shape

        # Process with MediaPipe
        results = pose.process(image_rgb)

        if not results.pose_landmarks:
            return {'success': False, 'message': 'No person detected in image'}

        # Extract landmarks
        landmarks = {}
        for idx, landmark in enumerate(results.pose_landmarks.landmark):
            landmarks[idx] = (landmark.x * width, landmark.y * height)

        # Estimate calibration
        pixels_per_cm = estimate_pixels_per_cm(landmarks, height)
        if not pixels_per_cm:
            return {'success': False, 'message': 'Unable to calibrate measurements'}

        # Calculate measurements
        measurements_px = {}

        # Shoulder Width (11 to 12)
        if 11 in landmarks and 12 in landmarks:
            measurements_px['shoulder'] = calculate_distance(landmarks[11], landmarks[12])

        # Hip Width (23 to 24)
        if 23 in landmarks and 24 in landmarks:
            measurements_px['hip'] = calculate_distance(landmarks[23], landmarks[24])

        # Waist (estimated)
        if 'shoulder' in measurements_px and 'hip' in measurements_px:
            measurements_px['waist'] = (measurements_px['shoulder'] + measurements_px['hip']) / 2 * 0.80

        # Chest (approximate as slightly larger than shoulder)
        if 'shoulder' in measurements_px:
            measurements_px['chest'] = measurements_px['shoulder'] * 1.2

        # Left Arm Length
        if 11 in landmarks and 13 in landmarks and 15 in landmarks:
            upper_arm = calculate_distance(landmarks[11], landmarks[13])
            forearm = calculate_distance(landmarks[13], landmarks[15])
            measurements_px['left_arm'] = upper_arm + forearm

        # Right Arm Length
        if 12 in landmarks and 14 in landmarks and 16 in landmarks:
            upper_arm = calculate_distance(landmarks[12], landmarks[14])
            forearm = calculate_distance(landmarks[14], landmarks[16])
            measurements_px['right_arm'] = upper_arm + forearm

        # Inseam (crotch to ankle)
        if 23 in landmarks and 24 in landmarks and 27 in landmarks and 25 in landmarks:
            crotch_x = (landmarks[23][0] + landmarks[24][0]) / 2
            crotch_y = (landmarks[23][1] + landmarks[24][1]) / 2
            upper_leg = calculate_distance((crotch_x, crotch_y), landmarks[25])
            lower_leg = calculate_distance(landmarks[25], landmarks[27])
            measurements_px['inseam'] = upper_leg + lower_leg

        # Torso Length (shoulder to hip)
        if 11 in landmarks and 23 in landmarks:
            measurements_px['torso'] = calculate_distance(landmarks[11], landmarks[23])

        # Convert all measurements to cm
        measurements_cm = {
            k: round(v / pixels_per_cm, 1) 
            for k, v in measurements_px.items()
        }

        return {
            'success': True,
            'measurements': measurements_cm
        }

    except Exception as e:
        return {'success': False, 'message': f'Processing error: {str(e)}'}

@app.route('/api/measure', methods=['POST'])
def measure():
    """Main endpoint for measurement processing"""
    try:
        # Check if image is in request
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image provided'}), 400

        file = request.files['image']
        
        # Read and validate image
        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert RGBA to RGB if needed
        if image.mode == 'RGBA':
            image = image.convert('RGB')

        # Process measurements
        result = process_image_measurements(image)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({
            'success': False
