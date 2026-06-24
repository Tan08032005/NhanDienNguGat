import cv2
import time
import pygame
import os
from drowsy_detection import VideoFrameHandler

# Khởi tạo pygame mixer
pygame.mixer.init()

# Tải file âm thanh
alarm_sound = None
try:
    alarm_sound = pygame.mixer.Sound("audio/wake_up.wav")
    alarm_sound.set_volume(0.8)
    print("Đã tải file âm thanh thành công!")
except Exception as e:
    print(f"Lỗi khi tải file âm thanh: {e}")

# Khởi tạo camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Không thể mở camera!")
    exit()

# Khởi tạo video handler
video_handler = VideoFrameHandler()

# Thiết lập ngưỡng
thresholds = {
    "EAR_THRESH": 0.25,
    "WAIT_TIME": 1.0,
    "MAR_THRESH": 0.6
}

print("Nhấn 'q' để thoát")
print("Nhấn 's' để test âm thanh")

is_alarm_playing = False

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Xử lý frame
    processed_frame, play_alarm = video_handler.process(frame, thresholds)
    
    # Phát âm thanh cảnh báo
    if play_alarm and alarm_sound and not is_alarm_playing:
        pygame.mixer.Sound.play(alarm_sound, loops=-1)  # Lặp vô hạn
        is_alarm_playing = True
        print("🚨 CẢNH BÁO: Phát hiện buồn ngủ!")
    elif not play_alarm and is_alarm_playing:
        pygame.mixer.stop()
        is_alarm_playing = False
        print("✅ Dừng cảnh báo")
    
    # Hiển thị frame
    cv2.imshow('Drowsy Detection', processed_frame)
    
    # Xử lý phím
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):  # Test âm thanh
        if alarm_sound:
            pygame.mixer.Sound.play(alarm_sound)
            print("🔊 Test âm thanh!")

# Dọn dẹp
pygame.mixer.stop()
cap.release()
cv2.destroyAllWindows()
print("Đã thoát chương trình")