import cv2
import mediapipe as mp

class PoseDetector:
    def __init__(self, mode=False, complexity=1, smooth=True, segmentation=False, smooth_segmentation=True, detection_con=0.5, track_con=0.5):
        self.mode = mode
        self.complexity = complexity
        self.smooth = smooth
        self.segmentation = segmentation
        self.smooth_segmentation = smooth_segmentation
        self.detection_con = detection_con
        self.track_con = track_con

        self.mp_draw = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=self.mode,
            model_complexity=self.complexity,
            smooth_landmarks=self.smooth,
            enable_segmentation=self.segmentation,
            smooth_segmentation=self.smooth_segmentation,
            min_detection_confidence=self.detection_con,
            min_tracking_confidence=self.track_con
        )

    def find_pose(self, img, draw=True):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.pose.process(img_rgb)
        
        if self.results.pose_landmarks:
            if draw:
                self.mp_draw.draw_landmarks(img, self.results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
        return img

    def get_position(self, img, draw=True):
        lm_list = []
        if self.results.pose_landmarks:
            for id, lm in enumerate(self.results.pose_landmarks.landmark):
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append([id, cx, cy, lm.visibility])
                if draw:
                    cv2.circle(img, (cx, cy), 5, (255, 0, 0), cv2.FILLED)
        return lm_list
