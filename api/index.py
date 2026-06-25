import os
import tempfile
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
from .video_3d_measurement_pipeline import Video3DMeasurementPipeline

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Measulor - 3D Video Measurement</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; color: #333; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; text-align: center; }
        .upload-section { margin: 30px 0; padding: 20px; border: 2px dashed #bdc3c7; border-radius: 8px; text-align: center; }
        .btn { background: #3498db; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-size: 16px; margin-top: 15px; }
        .btn:hover { background: #2980b9; }
        #status { margin: 20px 0; font-weight: bold; color: #e67e22; text-align: center; }
        #results { display: none; background: #f8f9fa; padding: 20px; border-radius: 8px; }
        .measure-item { display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #dee2e6; }
        .spinner { display: none; border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <h1>Measulor 3D Pipeline</h1>
        <p style="text-align: center;">Upload a video to reconstruct a 3D model and extract measurements using COLMAP & Open3D.</p>
        
        <div class="upload-section">
            <input type="file" id="videoFile" accept="video/mp4,video/mov,video/avi" />
            <br/>
            <label style="display:inline-block; margin-top: 10px;">Reference Height (cm): 
                <input type="number" id="height_cm" placeholder="e.g. 170" value="170" />
            </label>
            <br/>
            <button class="btn" onclick="uploadVideo()">Process Video</button>
        </div>
        
        <div id="status"></div>
        <div class="spinner" id="spinner"></div>
        
        <div id="results"></div>
    </div>

    <script>
        async function uploadVideo() {
            const fileInput = document.getElementById('videoFile');
            const heightInput = document.getElementById('height_cm');
            const statusDiv = document.getElementById('status');
            const spinner = document.getElementById('spinner');
            const resultsDiv = document.getElementById('results');
            
            if (!fileInput.files.length) {
                alert('Please select a video file.');
                return;
            }
            
            const formData = new FormData();
            formData.append('video', fileInput.files[0]);
            if (heightInput.value) {
                formData.append('height_cm', heightInput.value);
            }
            
            statusDiv.innerText = 'Processing video... This may take several minutes as COLMAP runs.';
            spinner.style.display = 'block';
            resultsDiv.style.display = 'none';
            
            try {
                const response = await fetch('/api/measure-video-3d', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                spinner.style.display = 'none';
                
                if (response.ok && data.success) {
                    statusDiv.innerText = 'Processing complete!';
                    
                    let mHtml = '<h3>Measurements:</h3>';
                    const m = data.data.key_measurements || {};
                    for (const [key, value] of Object.entries(m)) {
                        mHtml += `<div class="measure-item"><strong>${key.replace(/_/g, ' ').toUpperCase()}</strong><span>${value}</span></div>`;
                    }
                    
                    let modelHtml = '<h3>3D Model Stats:</h3>';
                    const ms = data.data['3d_model'] || {};
                    for (const [key, value] of Object.entries(ms)) {
                        modelHtml += `<div class="measure-item"><strong>${key}</strong><span>${value}</span></div>`;
                    }
                    
                    resultsDiv.innerHTML = mHtml + modelHtml;
                    resultsDiv.style.display = 'block';
                } else {
                    statusDiv.innerText = 'Error: ' + (data.message || 'Unknown error');
                }
            } catch (err) {
                spinner.style.display = 'none';
                statusDiv.innerText = 'Failed to process: ' + err.message;
            }
        }
    </script>
</body>
</html>
    ''')

@app.route('/api/measure-video-3d', methods=['POST'])
def measure_video_3d():
    try:
        if 'video' not in request.files:
            return jsonify({'success': False, 'message': 'No video file provided'}), 400
        
        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({'success': False, 'message': 'No video file selected'}), 400
            
        reference_height = request.form.get('height_cm', type=float)
        
        temp_path = os.path.join(tempfile.gettempdir(), 'upload_' + video_file.filename)
        video_file.save(temp_path)
        
        pipeline = Video3DMeasurementPipeline(reference_height)
        success, result = pipeline.process_video(temp_path, max_frames=30)
        
        try:
            os.remove(temp_path)
        except:
            pass
            
        if success:
            summary = pipeline.get_summary()
            return jsonify({
                'success': True,
                'data': summary,
                'pipeline': '3D reconstruction'
            })
        else:
            return jsonify({'success': False, 'message': result}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
