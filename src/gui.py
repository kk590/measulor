import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
from .pose_detector import PoseDetector
from .image_recognition import ReferenceObjectDetector, BodyShapeClassifier
from .measurement import MeasurementCalculator
from .utils import resize_image

class App:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)

        self.video_source = 0
        self.vid = cv2.VideoCapture(self.video_source)

        self.canvas = tk.Canvas(window, width=800, height=600)
        self.canvas.pack(side=tk.LEFT)

        # Sidebar
        self.sidebar = tk.Frame(window, width=200, height=600, bg='white')
        self.sidebar.pack(side=tk.RIGHT, fill=tk.Y)

        self.btn_calibrate = tk.Button(self.sidebar, text="Auto-Calibrate", width=20, command=self.calibrate)
        self.btn_calibrate.pack(pady=10)

        self.lbl_status = tk.Label(self.sidebar, text="Status: Ready", bg='white')
        self.lbl_status.pack(pady=5)

        self.lbl_measurements = tk.Label(self.sidebar, text="Measurements:", bg='white', font=("Arial", 12, "bold"))
        self.lbl_measurements.pack(pady=20)

        self.measurement_labels = {}
        for m in ['Shoulder', 'Waist', 'Hip', 'Left Arm', 'Right Arm', 'Inseam', 'Outer Leg']:
            lbl = tk.Label(self.sidebar, text=f"{m}: -- cm", bg='white')
            lbl.pack(anchor='w', padx=10)
            self.measurement_labels[m] = lbl

        self.lbl_shape = tk.Label(self.sidebar, text="Shape: --", bg='white', font=("Arial", 12, "bold"))
        self.lbl_shape.pack(pady=20)

        # Logic modules
        self.detector = PoseDetector()
        self.ref_detector = ReferenceObjectDetector()
        self.calculator = MeasurementCalculator()
        self.shape_classifier = BodyShapeClassifier()

        self.is_calibrated = False
        self.delay = 15
        self.update()

        self.window.mainloop()

    def calibrate(self):
        ret, frame = self.vid.read()
        if ret:
            pixels_per_cm, img_with_ref = self.ref_detector.detect_reference(frame)
            if pixels_per_cm:
                self.calculator.set_calibration(pixels_per_cm)
                self.is_calibrated = True
                self.lbl_status.config(text="Status: Calibrated", fg="green")
            else:
                self.lbl_status.config(text="Status: Ref Object Not Found", fg="red")

    def update(self):
        ret, frame = self.vid.read()
        if ret:
            # 1. Detect Pose
            frame = self.detector.find_pose(frame)
            lm_list = self.detector.get_position(frame, draw=False)

            # 2. Calculate Measurements
            if self.is_calibrated and lm_list:
                measurements = self.calculator.calculate(lm_list)
                
                # Update UI
                for k, v in measurements.items():
                    key_map = {
                        'shoulder': 'Shoulder', 
                        'waist': 'Waist', 
                        'hip': 'Hip', 
                        'left_arm': 'Left Arm',
                        'right_arm': 'Right Arm',
                        'inseam': 'Inseam',
                        'outer_leg': 'Outer Leg'
                    }
                    if k in key_map:
                        self.measurement_labels[key_map[k]].config(text=f"{key_map[k]}: {v:.1f} cm")
                
                # 3. Classify Shape
                shape = self.shape_classifier.classify(measurements)
                self.lbl_shape.config(text=f"Shape: {shape}")

            # Display Video
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = resize_image(frame, width=800)
            self.photo = ImageTk.PhotoImage(image=Image.fromarray(frame))
            self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

        self.window.after(self.delay, self.update)
