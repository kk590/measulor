import os
from flask import Flask, render_template_string

# Import the measure app to get its routes
from api.measure import app as measure_app

# Use the existing Flask app
app = measure_app

# Add homepage route
@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Measulor - AI Body Measurement (Full Version)</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 40px;
            max-width: 600px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
        }
        h1 { color: #667eea; margin-bottom: 10px; font-size: 2.5em; }
        .badge {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 20px;
            border-radius: 20px;
            display: inline-block;
            margin-bottom: 20px;
            font-size: 0.9em;
        }
        p { color: #555; line-height: 1.8; margin-bottom: 30px; }
        .features {
            text-align: left;
            margin: 30px 0;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
        }
        .features li {
            margin: 10px 0;
            color: #333;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 40px;
            border: none;
            border-radius: 25px;
            font-size: 1.1em;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin-top: 20px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        .btn:hover { transform: translateY(-2px); }
        .info { color: #888; font-size: 0.9em; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>💪 Measulor</h1>
        <div class="badge">✨ FULL AI VERSION - MediaPipe Powered</div>
        <p>Get accurate body measurements using advanced AI technology. This is the full version with real MediaPipe pose detection.</p>
        
        <div class="features">
            <h3 style="margin-bottom: 15px; color: #667eea;">✅ Features:</h3>
            <ul>
                <li>🧠 Real AI-powered measurements (MediaPipe)</li>
                <li>📏 Measure: Shoulders, Chest, Waist, Hips, Arms, Legs</li>
                <li>📸 Upload photos or use camera</li>
                <li>📊 Track your measurements over time</li>
                <li>💾 Export data as CSV/PDF</li>
            </ul>
        </div>
        
        <a href="https://measulor.vercel.app" class="btn">🚀 Try Demo Version</a>
        
        <div class="info">
            <p><strong>API Endpoint:</strong> POST /api/measure</p>
            <p>This Railway deployment provides the full MediaPipe backend API.</p>
        </div>
    </div>
</body>
</html>
    ''')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
