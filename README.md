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
    pip install -r requirements.txt
    ```

## Usage

1.  Run the application:
    ```bash
    python main.py
    ```

2.  **Calibration**:
    -   Hold a standard credit card (8.56cm width) against your chest/body visible to the camera.
    -   Click "Auto-Calibrate".
    -   Ensure the green rectangle detects the card correctly.

3.  **Measurement**:
    -   Step back so your full body is visible.
    -   Stand in a T-pose or A-pose.
    -   Measurements will appear on the sidebar.

## Requirements
-   Python 3.8+
-   Webcam

## License
MIT
