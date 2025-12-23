from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return '''<!DOCTYPE html>
<html>
<head>
    <title>Measulor - AI Body Measurement Tool</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            color: white;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
            text-align: center;
        }
        h1 {
            font-size: 3em;
            margin-bottom: 20px;
        }
        p {
            font-size: 1.2em;
            margin-bottom: 15px;
            line-height: 1.6;
        }
        .success {
            background: #48bb78;
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>👕 Measulor</h1>
        <h2>AI Body Measurement Tool</h2>
        <div class="success">✅ Deployment Successful!</div>
        <p>Your Flask application is now running on Vercel.</p>
        <p>This is a body measurement tool using Computer Vision.</p>
        <p><strong>Note:</strong> The webcam-based measurement feature requires local execution with camera access. For web deployment, we'll need to implement browser-based image capture and processing.</p>
    </div>
</body>
</html>'''

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Flask app is running!'})

if __name__ == '__main__':
    app.run()
