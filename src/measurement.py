from .utils import calculate_distance

class MeasurementCalculator:
    def __init__(self):
        self.pixels_per_cm = None

    def set_calibration(self, pixels_per_cm):
        self.pixels_per_cm = pixels_per_cm

    def calculate(self, landmarks):
        """
        Calculate measurements from landmarks.
        landmarks: List of [id, x, y, visibility]
        """
        if not landmarks or self.pixels_per_cm is None:
            return {}

        # Map landmarks by ID for easy access
        lm_dict = {lm[0]: (lm[1], lm[2]) for lm in landmarks}

        # MediaPipe Pose Landmark IDs:
        # 11: left_shoulder, 12: right_shoulder
        # 23: left_hip, 24: right_hip
        # 13: left_elbow, 14: right_elbow
        # 15: left_wrist, 16: right_wrist

        measurements_px = {}
        
        # Shoulder Width (11 to 12)
        if 11 in lm_dict and 12 in lm_dict:
            measurements_px['shoulder'] = calculate_distance(lm_dict[11], lm_dict[12])

        # Hip Width (23 to 24)
        if 23 in lm_dict and 24 in lm_dict:
            measurements_px['hip'] = calculate_distance(lm_dict[23], lm_dict[24])

        # Waist Estimation
        # We approximate the waist level. For a better guess, we can use the midpoint between shoulder and hip vertical level,
        # but since we don't have width at that specific point from landmarks, we often estimate it.
        # A simple heuristic is often used: Waist < Hip usually.
        # Let's try to simulate a point between the lowest rib (not available) and hip.
        # We will use a geometric approximation: 0.85 * average of (shoulder width and hip width) is very rough.
        # A slightly better approach for 2D frontal view: 
        # The body contour is not available from pose landmarks alone (segmentation mask would be needed for true width).
        # We will stick to the heuristic but refine it slightly or just acknowledge it's an estimate.
        if 'shoulder' in measurements_px and 'hip' in measurements_px:
             measurements_px['waist'] = (measurements_px['shoulder'] + measurements_px['hip']) / 2 * 0.80

        # Left Arm Length (11 to 13 + 13 to 15)
        if 11 in lm_dict and 13 in lm_dict and 15 in lm_dict:
            upper_arm = calculate_distance(lm_dict[11], lm_dict[13])
            forearm = calculate_distance(lm_dict[13], lm_dict[15])
            measurements_px['left_arm'] = upper_arm + forearm

        # Right Arm Length (12 to 14 + 14 to 16)
        if 12 in lm_dict and 14 in lm_dict and 16 in lm_dict:
            upper_arm = calculate_distance(lm_dict[12], lm_dict[14])
            forearm = calculate_distance(lm_dict[14], lm_dict[16])
            measurements_px['right_arm'] = upper_arm + forearm

        # Inside Leg (Inseam) - Approximation
        # Ideally from crotch to ankle. MediaPipe doesn't have a crotch point.
        # We can approximate crotch as midpoint between hips (23, 24).
        # Then distance to ankle (27 left, 28 right).
        if 23 in lm_dict and 24 in lm_dict and 27 in lm_dict:
            crotch_x = (lm_dict[23][0] + lm_dict[24][0]) / 2
            crotch_y = (lm_dict[23][1] + lm_dict[24][1]) / 2
            
            # Distance from crotch to left ankle (27) - often broken into thigh + calf if knee is bent, 
            # but for standing straight, direct often works. Better: crotch->knee + knee->ankle
            if 25 in lm_dict: # Left knee
                 upper_leg = calculate_distance((crotch_x, crotch_y), lm_dict[25])
                 lower_leg = calculate_distance(lm_dict[25], lm_dict[27])
                 measurements_px['inseam'] = upper_leg + lower_leg
            else:
                 measurements_px['inseam'] = calculate_distance((crotch_x, crotch_y), lm_dict[27])

        # Outer Leg (Waist/Hip to Ankle) - usually measured from waist, but here hip (23) to ankle (27)
        if 23 in lm_dict and 25 in lm_dict and 27 in lm_dict:
            upper_leg = calculate_distance(lm_dict[23], lm_dict[25])
            lower_leg = calculate_distance(lm_dict[25], lm_dict[27])
            measurements_px['outer_leg'] = upper_leg + lower_leg

        # Convert to cm
        measurements_cm = {k: v / self.pixels_per_cm for k, v in measurements_px.items()}
        
        return measurements_cm
