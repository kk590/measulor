"""Tool 1: Video Upload API Endpoint
Handles video file uploads with validation and temporary storage
"""

from flask import request, jsonify
import os
import tempfile
from werkzeug.utils import secure_filename

# Allowed video formats
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'webm', 'mkv'}

# Maximum file size (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_video_size(file):
    """Check if video file size is within limits"""
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    return file_size <= MAX_FILE_SIZE

def save_uploaded_video(video_file):
    """
    Save uploaded video to temporary directory
    Returns: (success, temp_path or error_message)
    """
    try:
        # Secure the filename
        filename = secure_filename(video_file.filename)
        
        # Check file extension
        if not allowed_file(filename):
            return False, f"Invalid file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        
        # Check file size
        if not validate_video_size(video_file):
            return False, f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        
        # Create temporary file
        suffix = '.' + filename.rsplit('.', 1)[1].lower()
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_path = temp_file.name
        
        # Save video to temporary file
        video_file.save(temp_path)
        temp_file.close()
        
        return True, temp_path
    
    except Exception as e:
        return False, f"Error saving video: {str(e)}"

def upload_video_endpoint():
    """Main endpoint handler for video upload"""
    try:
        # Check if video file is in request
        if 'video' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No video file provided'
            }), 400
        
        video_file = request.files['video']
        
        # Check if file is empty
        if video_file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No video file selected'
            }), 400
        
        # Save video file
        success, result = save_uploaded_video(video_file)
        
        if not success:
            return jsonify({
                'success': False,
                'message': result
            }), 400
        
        # Return success with temp file path
        return jsonify({
            'success': True,
            'message': 'Video uploaded successfully',
            'temp_path': result,
            'filename': secure_filename(video_file.filename)
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Upload error: {str(e)}'
        }), 500

def cleanup_temp_file(temp_path):
    """Delete temporary video file after processing"""
    try:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
            return True
    except Exception as e:
        print(f"Error cleaning up temp file: {e}")
        return False

def validate_video(video_path):
    """
    Validate video file and extract basic information
    Returns: (success, video_info_or_error)
    """
    try:
        import cv2
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return False, {'error': 'Unable to open video file'}
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Calculate duration
        duration = frame_count / fps if fps > 0 else 0
        
        cap.release()
        
        # Validate video properties
        if width == 0 or height == 0:
            return False, {'error': 'Invalid video dimensions'}
        
        if fps == 0:
            return False, {'error': 'Unable to determine video frame rate'}
        
        return True, {
            'width': width,
            'height': height,
            'fps': fps,
            'frame_count': frame_count,
            'duration': duration,
            'file_path': video_path
        }
    
    except ImportError:
        return False, {'error': 'OpenCV (cv2) not installed'}
    except Exception as e:
        return False, {'error': f'Video validation failed: {str(e)}'}
