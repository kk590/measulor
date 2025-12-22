# Measulor - AI Body Measurement Tool

Measulor is a Python-based application that uses Computer Vision (OpenCV, MediaPipe) to estimate body measurements from a webcam feed.

## Features
- **Real-time Pose Detection**: Uses MediaPipe Pose to track body landmarks.
- **Auto-Calibration**: Uses a standard reference object (Credit Card) to calculate pixel-to-cm ratio.
- **Body Measurements**: Estimates Shoulder Width, Hip Width, Waist (approx), Arm Length, Inseam, and Outer Leg.
- **Body Shape Classification**: simple heuristic classification (Hourglass, Pear, etc.).
- **GUI**: User-friendly interface built with Tkinter.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/measulor.git
    cd measulor
    ```

2.  Install dependencies:
   ```bash
   pip install -r requirements-desktop.txt
   ```
   
   **Important:** Use `requirements-desktop.txt` for local development. This includes `opencv-python` (with camera support) instead of `opencv-python-headless`.

## Usage

1. **Make sure your webcam is connected**

2. **Run the application:**
   ```bash
   python main.py
   ```

3. **Calibration:**
   - Hold a standard credit card (8.56cm width) against your chest/body visible to the camera.
   - Click "Auto-Calibrate".
   - Ensure the green rectangle detects the card correctly.

4. **Measurement:**
   - Step back so your full body is visible.
   - Stand in a T-pose or A-pose.
   - Measurements will appear on the sidebar.

## Requirements

- **Python 3.8-3.11** (Python 3.13 not supported yet)
- Webcam

## Troubleshooting

### Python 3.13 Compatibility Error

If you see `AttributeError: _ARRAY_API not found` or `numpy.core.multiarray failed to import`:

1. **Install Python 3.10:**
   - Download from: https://www.python.org/downloads/release/python-31011/
   
2. **Run with Python 3.10:**
   ```bash
   py -3.10 -m pip install -r requirements-desktop.txt
   py -3.10 main.py
   ```

### Camera Not Working

Make sure:
- Your webcam is connected and enabled
- No other application is using the camera
- You're using `requirements-desktop.txt` (not `requirements.txt`)

## License

MIT
