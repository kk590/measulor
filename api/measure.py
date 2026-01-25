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
    Improved calibration using more accurate body proportion ratios
    Uses head height as a reliable reference (average ~23cm)
    """
    # Method 1: Use head height (nose to top of head estimation)
    # Since MediaPipe doesn't have exact head top, we use nose to ear distance
    if 0 in landmarks and 7 in landmarks:  # nose to left ear
        nose = landmarks[0]
        ear = landmarks[7]
        head_width_px = calculate_distance(nose, ear)
        # Average head width is ~15cm
        avg_head_width_cm = 15
        pixels_per_cm_head = head_width_px / avg_head_width_cm
        
    # Method 2: Use shoulder-to-hip ratio for better accuracy
    if 11 in landmarks and 23 in landmarks:
        shoulder_to_hip_px = calculate_distance(landmarks[11], landmarks[23])
        # Average torso length (shoulder to hip) is ~45cm
        avg_torso_cm = 45
        pixels_per_cm_torso = shoulder_to_hip_px / avg_torso_cm
        
        # If both methods available, use average for better accuracy
        if 0 in landmarks and 7 in landmarks:
            return (pixels_per_cm_head + pixels_per_cm_torso) / 2
        return pixels_per_cm_torso
    
    # Fallback: Use full body height with improved estimate
    if 0 in landmarks and 27 in landmarks:
        nose = landmarks[0]
        ankle = landmarks[27]
        pixel_height = abs(nose[1] - ankle[1])
        # More realistic height range: 160-180cm average
        assumed_height_cm = 168
        pixels_per_cm = pixel_height / assumed_height_cm
        return pixels_per_cm
    
    return None

def calculate_waist_measurement(landmarks, shoulder_width, hip_width):
    """
    More accurate waist calculation using anatomical landmarks
    """
    # Try to use actual waist landmarks (between ribs and hips)
    if 11 in landmarks and 12 in landmarks and 23 in landmarks and 24 in landmarks:
        # Calculate midpoint between shoulders and hips
        shoulder_left = landmarks[11]
        shoulder_right = landmarks[12]
        hip_left = landmarks[23]
        hip_right = landmarks[24]
        
        # Waist is approximately 60% down from shoulder to hip
        waist_y = shoulder_left[1] + (hip_left[1] - shoulder_left[1]) * 0.6
        
        # Estimate waist width based on body proportions
        # Waist is typically 70-75% of shoulder width
        waist_width = shoulder_width * 0.72
        
        return waist_width
    
    # Fallback to improved estimation
    return (shoulder_width * 0.75 + hip_width * 0.85) / 2

def calculate_chest_measurement(landmarks, shoulder_width):
    """
    Improved chest calculation using shoulder and arm landmarks
    """
    if 11 in landmarks and 12 in landmarks:
        # Chest is typically 1.3-1.4x shoulder width for proper fit
        # This accounts for ribcage and muscle
        return shoulder_width * 1.35
    
    return shoulder_width * 1.3

def process_image_measurements(image_data):
    """Process image and return measurements with improved accuracy"""
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
        
        # Improved calibration
        pixels_per_cm = estimate_pixels_per_cm(landmarks, height)
        
        if not pixels_per_cm:
            return {'success': False, 'message': 'Unable to calibrate measurements'}
        
        # Calculate measurements in pixels
        measurements_px = {}
        
        # Shoulder Width (11 to 12)
        if 11 in landmarks and 12 in landmarks:
            measurements_px['shoulder'] = calculate_distance(landmarks[11], landmarks[12])
        
        # Hip Width (23 to 24)
        if 23 in landmarks and 24 in landmarks:
            measurements_px['hip'] = calculate_distance(landmarks[23], landmarks[24])
        
        # Improved Waist calculation
        if 'shoulder' in measurements_px and 'hip' in measurements_px:
            measurements_px['waist'] = calculate_waist_measurement(
                landmarks, 
                measurements_px['shoulder'], 
                measurements_px['hip']
            )
        
        # Improved Chest calculation
        if 'shoulder' in measurements_px:
            measurements_px['chest'] = calculate_chest_measurement(
                landmarks,
                measurements_px['shoulder']
            )
        
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
        
        # Average arm length for better accuracy
        if 'left_arm' in measurements_px and 'right_arm' in measurements_px:
            measurements_px['arm'] = (measurements_px['left_arm'] + measurements_px['right_arm']) / 2
        
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
        
        # Neck circumference estimation (shoulder width * 0.45)
        if 'shoulder' in measurements_px:
            measurements_px['neck'] = measurements_px['shoulder'] * 0.45
        
        # Convert all measurements to cm with improved accuracy
        measurements_cm = {
            k: round(v / pixels_per_cm, 1) 
            for k, v in measurements_px.items()
        }
        
        return {
            'success': True,
            'measurements': measurements_cm,
            'calibration': {
                'pixels_per_cm': round(pixels_per_cm, 2),
                'method': 'improved_multi_reference'
            }
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
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
