import cv2
import time
import numpy as np
import mediapipe as mp
from mediapipe.python.solutions.drawing_utils import _normalized_to_pixel_coordinates as denormalize_coordinates

# ========== Các hàm tiện ích ==========

def distance(p1, p2):
    return sum([(i - j) ** 2 for i, j in zip(p1, p2)]) ** 0.5

def get_ear(landmarks, refer_idxs, frame_w, frame_h):
    """Tính EAR cho 1 mắt"""
    try:
        coords_points = []
        for i in refer_idxs:
            lm = landmarks[i]
            coord = denormalize_coordinates(lm.x, lm.y, frame_w, frame_h)
            coords_points.append(coord)

        P2_P6 = distance(coords_points[1], coords_points[5])
        P3_P5 = distance(coords_points[2], coords_points[4])
        P1_P4 = distance(coords_points[0], coords_points[3])

        ear = (P2_P6 + P3_P5) / (2.0 * P1_P4)
    except:
        ear = 0.0
        coords_points = None

    return ear, coords_points

def calculate_avg_ear(landmarks, left_eye_idxs, right_eye_idxs, image_w, image_h):
    left_ear, left_coords = get_ear(landmarks, left_eye_idxs, image_w, image_h)
    right_ear, right_coords = get_ear(landmarks, right_eye_idxs, image_w, image_h)
    avg_ear = (left_ear + right_ear) / 2.0
    return avg_ear, (left_coords, right_coords)

def get_mar(landmarks, frame_w, frame_h):
    """Tính MAR cho miệng"""
    try:
        top = denormalize_coordinates(landmarks[13].x, landmarks[13].y, frame_w, frame_h)
        bottom = denormalize_coordinates(landmarks[14].x, landmarks[14].y, frame_w, frame_h)
        left = denormalize_coordinates(landmarks[78].x, landmarks[78].y, frame_w, frame_h)
        right = denormalize_coordinates(landmarks[308].x, landmarks[308].y, frame_w, frame_h)

        vertical = distance(top, bottom)
        horizontal = distance(left, right)
        mar = vertical / horizontal
    except:
        mar = 0.0
    return mar

def get_mediapipe_app(max_num_faces=1, refine_landmarks=False,
                      min_detection_confidence=0.7, min_tracking_confidence=0.7):
    return mp.solutions.face_mesh.FaceMesh(
        max_num_faces=max_num_faces,
        refine_landmarks=refine_landmarks,
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
    )

def plot_eye_landmarks(frame, left_coords, right_coords, color):
    for lm_coordinates in [left_coords, right_coords]:
        if lm_coordinates:
            for coord in lm_coordinates:
                cv2.circle(frame, coord, 2, color, -1)
    return frame

def plot_text(image, text, origin, color,
              font=cv2.FONT_HERSHEY_SIMPLEX, fntScale=0.8, thickness=2):
    return cv2.putText(image, text, origin, font, fntScale, color, thickness)

def draw_warning_box(frame, title, subtitle="Buon ngu!", action="Can nghi ngoi"):
    """Vẽ hộp cảnh báo góc trên-phải trên khung camera."""
    frame_h, frame_w = frame.shape[:2]
    box_w, box_h = 300, 110
    margin = 12
    x1 = frame_w - box_w - margin
    y1 = margin
    x2 = x1 + box_w
    y2 = y1 + box_h

    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)

    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, title, (x1 + 12, y1 + 32), font, 0.72, (255, 255, 255), 2)
    cv2.putText(frame, subtitle, (x1 + 12, y1 + 62), font, 0.62, (255, 255, 255), 2)
    cv2.putText(frame, action, (x1 + 12, y1 + 92), font, 0.62, (255, 255, 255), 2)
    return frame

def plot_mouth_landmarks(frame, landmarks, frame_w, frame_h, color):
    mouth_idxs = [13, 14, 78, 308]  # trên, dưới, trái, phải
    for i in mouth_idxs:
        lm = landmarks[i]
        coord = denormalize_coordinates(lm.x, lm.y, frame_w, frame_h)
        if coord:
            cv2.circle(frame, coord, 2, color, -1)
    return frame

# ========== VideoFrameHandler class ==========

class VideoFrameHandler:
    def __init__(self):
        self.eye_idxs = {
            "left": [362, 385, 387, 263, 373, 380],
            "right": [33, 160, 158, 133, 153, 144],
        }

        self.RED = (0, 0, 255)
        self.GREEN = (0, 255, 0)

        self.facemesh_model = get_mediapipe_app()

        self.state_tracker = {
            "start_time": time.perf_counter(),
            "DROWSY_TIME": 0.0,
            "COLOR": self.GREEN,
            "play_alarm": False,
            "yawn": False,
        }

        self.EAR_txt_pos = (10, 30)

    def process(self, frame: np.ndarray, thresholds: dict):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.facemesh_model.process(rgb_frame)

        frame_h, frame_w, _ = frame.shape
        DROWSY_TIME_txt_pos = (10, int(frame_h * 0.85))
        ALM_txt_pos = (10, int(frame_h * 0.92))
        MAR_txt_pos = (10, int(frame_h * 0.78))

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            EAR, coordinates = calculate_avg_ear(
                landmarks, self.eye_idxs["left"], self.eye_idxs["right"], frame_w, frame_h
            )
            MAR = get_mar(landmarks, frame_w, frame_h)

            frame = plot_eye_landmarks(frame, coordinates[0], coordinates[1], self.state_tracker["COLOR"])
            frame = plot_mouth_landmarks(frame, landmarks, frame_w, frame_h, self.state_tracker["COLOR"])

            # --- Kiểm tra nhắm mắt ---
            is_drowsy = False
            if EAR < thresholds["EAR_THRESH"]:
                end_time = time.perf_counter()
                self.state_tracker["DROWSY_TIME"] += end_time - self.state_tracker["start_time"]
                self.state_tracker["start_time"] = end_time
                self.state_tracker["COLOR"] = self.RED

                if self.state_tracker["DROWSY_TIME"] >= thresholds["WAIT_TIME"]:
                    is_drowsy = True
            else:
                self.state_tracker["start_time"] = time.perf_counter()
                self.state_tracker["DROWSY_TIME"] = 0.0
                self.state_tracker["COLOR"] = self.GREEN

            # --- Kiểm tra ngáp ---
            is_yawn = MAR > thresholds["MAR_THRESH"]
            self.state_tracker["yawn"] = is_yawn
            self.state_tracker["play_alarm"] = is_drowsy or is_yawn

            if is_yawn:
                plot_text(frame, "YAWNING!", (10, int(frame_h * 0.97)), self.RED)
                frame = draw_warning_box(frame, "CANH BAO NGAP!")
            elif is_drowsy:
                plot_text(frame, "WAKE UP! WAKE UP!", ALM_txt_pos, self.RED)
                frame = draw_warning_box(frame, "CANH BAO NGU GAT!")

            # --- Hiển thị số liệu ---
            EAR_txt = f"EAR: {round(EAR, 2)}"
            DROWSY_TIME_txt = f"DROWSY: {round(self.state_tracker['DROWSY_TIME'], 2)}s"
            MAR_txt = f"MAR: {round(MAR, 2)}"

            plot_text(frame, EAR_txt, self.EAR_txt_pos, self.state_tracker["COLOR"])
            plot_text(frame, DROWSY_TIME_txt, DROWSY_TIME_txt_pos, self.state_tracker["COLOR"])
            plot_text(frame, MAR_txt, MAR_txt_pos, self.state_tracker["COLOR"])

        else:
            self.state_tracker["start_time"] = time.perf_counter()
            self.state_tracker["DROWSY_TIME"] = 0.0
            self.state_tracker["COLOR"] = self.GREEN
            self.state_tracker["play_alarm"] = False
            self.state_tracker["yawn"] = False

        return frame, self.state_tracker["play_alarm"]
