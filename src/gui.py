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
        
        # Main container
        self.main_frame = tk.Frame(window)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas for video
        self.canvas = tk.Canvas(self.main_frame, width=800, height=600, bg='black')
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Sidebar
        self.sidebar = tk.Frame(self.main_frame, width=250, bg='white')
        self.sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        self.sidebar.pack_propagate(False)
        
        # Calibrate button
        self.btn_calibrate = tk.Button(self.sidebar, text="Auto-Calibrate", width=25, 
                                       command=self.calibrate, bg='#4CAF50', fg='white', 
                                       font=("Arial", 10, "bold"))
        self.btn_calibrate.pack(pady=10)
        
        # Status label
        self.lbl_status = tk.Label(self.sidebar, text="Status: Ready", bg='white', 
                                   font=("Arial", 10), fg='black')
        self.lbl_status.pack(pady=5)
        
        # Measurements header
        self.lbl_measurements = tk.Label(self.sidebar, text="Measurements:", bg='white', 
                                        font=("Arial", 12, "bold"))
        self.lbl_measurements.pack(pady=15)
        
        # Measurement labels
        self.measurement_labels = {}
        measurements_list = ['Shoulder', 'Waist', 'Hip', 'Left Arm', 'Right Arm', 'Inseam', 'Outer Leg']
        
        for m in measurements_list:
            lbl = tk.Label(self.sidebar, text=f"{m}: -- cm", bg='white', 
                          font=("Arial", 9), justify=tk.LEFT)
            lbl.pack(anchor='w', padx=10, pady=3)
            self.measurement_labels[m] = lbl
        
        # Shape label
        self.lbl_shape = tk.Label(self.sidebar, text="Shape: --", bg='white', 
                                 font=("Arial", 12, "bold"), fg='#2196F3')
        self.lbl_shape.pack(pady=20)
        
        # Initialize logic modules
        try:
            self.detector = PoseDetector()
            self.ref_detector = ReferenceObjectDetector()
            self.calculator = MeasurementCalculator()
            self.shape_classifier = BodyShapeClassifier()
        except Exception as e:
            self.lbl_status.config(text=f"Error: {str(e)}", fg='red')
            print(f"Initialization error: {e}")
        
        self.is_calibrated = False
        self.delay = 15
        self.photo = None  # Keep reference to prevent garbage collection
        
        self.update()
        self.window.mainloop()
    
    def calibrate(self):
        """Calibrate using a reference object"""
        ret, frame = self.vid.read()
        if ret:
            try:
                pixels_per_cm, img_with_ref = self.ref_detector.detect_reference(frame)
                if pixels_per_cm and pixels_per_cm > 0:
                    self.calculator.set_calibration(pixels_per_cm)
                    self.is_calibrated = True
                    self.lbl_status.config(text="Status: Calibrated ✓", fg="green")
                else:
                    self.lbl_status.config(text="Status: Ref Object Not Found", fg="red")
            except Exception as e:
                self.lbl_status.config(text=f"Calibration Error", fg="red")
                print(f"Calibration error: {e}")
    
    def update(self):
        """Update video feed and measurements"""
        try:
            ret, frame = self.vid.read()
            if ret:
                # 1. Detect Pose
                frame = self.detector.find_pose(frame)
                lm_list = self.detector.get_position(frame, draw=False)
                
                # 2. Calculate Measurements
                if self.is_calibrated and lm_list:
                    try:
                        measurements = self.calculator.calculate(lm_list)
                        
                        # Update UI with measurements
                        key_map = {
                            'shoulder': 'Shoulder', 
                            'waist': 'Waist', 
                            'hip': 'Hip', 
                            'left_arm': 'Left Arm',
                            'right_arm': 'Right Arm',
                            'inseam': 'Inseam',
                            'outer_leg': 'Outer Leg'
                        }
                        
                        for k, v in measurements.items():
                            if k in key_map and v is not None:
                                display_key = key_map[k]
                                self.measurement_labels[display_key].config(
                                    text=f"{display_key}: {v:.1f} cm"
                                )
                        
                        # 3. Classify Shape
                        shape = self.shape_classifier.classify(measurements)
                        if shape:
                            self.lbl_shape.config(text=f"Shape: {shape}")
                    except Exception as e:
                        print(f"Measurement calculation error: {e}")
                
                # Display Video
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = resize_image(frame, width=800)
                image = Image.fromarray(frame)
                self.photo = ImageTk.PhotoImage(image=image)
                self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
        except Exception as e:
            print(f"Update loop error: {e}")
        
        self.window.after(self.delay, self.update)
