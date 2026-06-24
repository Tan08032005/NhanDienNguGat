import os
import av
import threading
import datetime  
import streamlit as st
import streamlit.components.v1 as components  
from streamlit_webrtc import VideoHTMLAttributes, webrtc_streamer, WebRtcMode
from streamlit_autorefresh import st_autorefresh

from drowsy_detection import VideoFrameHandler
from audio_handling import AudioFrameHandler  

st.set_page_config(page_title="Nhận diện tài xế ngủ gật", layout="wide")

# 1. Khởi tạo State cố định cho giao diện chính
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

if "history" not in st.session_state:
    st.session_state["history"] = []

# Tự động làm mới giao diện mỗi 1 giây để kéo log ngầm lên màn hình
st_autorefresh(interval=1000, limit=10000, key="log_counter")

col_top_left, col_top_right = st.columns([5, 1])
with col_top_right:
    theme_btn = st.button("☀️ Chế độ Sáng" if st.session_state["theme"] == "dark" else "🌙 Chế độ Tối", use_container_width=True)
    if theme_btn:
        st.session_state["theme"] = "light" if st.session_state["theme"] == "dark" else "dark"
        st.rerun()

theme_class = "dark-theme" if st.session_state["theme"] == "dark" else "light-theme"
with open("index.html", "r", encoding="utf-8") as f:
    html_header = f.read().replace("{{THEME_CLASS}}", theme_class)
components.html(html_header, height=120)

# CSS Custom Themes
if st.session_state["theme"] == "dark":
    st.markdown("""<style>.stApp { background-color: #0b0f19 !important; } h3 { color: #ffffff !important; font-weight: 600 !important; } .stSlider p { color: #ef4444 !important; } div[data-baseweb="slider"] div { color: #ef4444 !important; } div[data-baseweb="slider"] { background-color: transparent !important; padding: 12px 0 !important; } div[data-baseweb="slider"] > div:first-child { background: #1f2937 !important; height: 6px !important; border-radius: 4px; } div[role="slider"] { background-color: #ef4444 !important; border: 2px solid #ffffff !important; width: 16px !important; height: 16px !important; } div[data-presentation="slider"] { color: #ef4444 !important; font-weight: bold; } div[element-type="button"] button, .stButton button { background-color: #1f2937 !important; color: #ffffff !important; border: 1px solid #374151 !important; border-radius: 8px !important; } div[element-type="button"] button:hover, .stButton button:hover { background-color: #ef4444 !important; color: white !important; }</style>""", unsafe_allow_html=True)
else:
    st.markdown("""<style>.stApp { background-color: #f8fafc !important; } h3 { color: #0f172a !important; font-weight: 600 !important; } div[data-baseweb="slider"] { background-color: transparent !important; padding: 12px 0 !important; } div[data-baseweb="slider"] > div:first-child { background: #e2e8f0 !important; height: 6px !important; border-radius: 4px; } div[role="slider"] { background-color: #3b82f6 !important; border: 2px solid #ffffff !important; width: 16px !important; height: 16px !important; } div[data-presentation="slider"] { color: #3b82f6 !important; font-weight: bold; } div[element-type="button"] button, .stButton button { background-color: #ffffff !important; color: #0f172a !important; border: 1px solid #cbd5e1 !important; border-radius: 8px !important; } div[element-type="button"] button:hover, .stButton button:hover { background-color: #3b82f6 !important; color: white !important; }</style>""", unsafe_allow_html=True)

# 2. KHỞI TẠO BIẾN TOÀN CỤC (Để luồng WebRTC ngầm tương tác an toàn)
if "video_handler" not in st.session_state:
    st.session_state["video_handler"] = VideoFrameHandler()
video_handler = st.session_state["video_handler"]

alarm_wav = os.path.join("audio", "wake_up.wav")
audio_handler = AudioFrameHandler(alarm_wav, volume=0.9, loop=False)

lock = threading.Lock()

# Sử dụng cấu trúc từ điển toàn cục để tránh đụng độ bộ nhớ của Streamlit State
if "shared_bridge" not in st.session_state:
    st.session_state["shared_bridge"] = {"play_alarm": False, "queue_logs": []}
shared_bridge = st.session_state["shared_bridge"]

col_main_left, col_main_right = st.columns([2, 1], gap="large")

with col_main_left:
    st.markdown("### 📷 Camera Giám Sát Realtime")
    
    col1, col2, col3 = st.columns(3)
    with col1: EAR_THRESH = st.slider("Ngưỡng mở mắt (EAR):", 0.0, 0.4, 0.25, 0.01)
    with col2: WAIT_TIME = st.slider("Thời gian chờ (giây):", 0.0, 5.0, 1.0, 0.25)
    with col3: MAR_THRESH = st.slider("Ngưỡng ngáp (MAR):", 0.0, 1.0, 0.6, 0.05)

    thresholds = {"EAR_THRESH": EAR_THRESH, "WAIT_TIME": WAIT_TIME, "MAR_THRESH": MAR_THRESH}

    def video_frame_callback(frame: av.VideoFrame):
        img = frame.to_ndarray(format="bgr24")
        img, play_alarm = video_handler.process(img, thresholds)
        
        with lock:
            if play_alarm and not shared_bridge["play_alarm"]:
                now = datetime.datetime.now().strftime("%H:%M:%S")
                shared_bridge["queue_logs"].append(f"⏱️ [{now}] Cảnh báo: Phát hiện ngủ gật / ngáp!")
            shared_bridge["play_alarm"] = play_alarm
            
        return av.VideoFrame.from_ndarray(img, format="bgr24")

    def audio_frame_callback(frame: av.AudioFrame):
        with lock:
            play_alarm = shared_bridge["play_alarm"]
        
        # Nếu không có báo động, trả về một frame "im lặng" để giữ kết nối không bị crash luồng âm thanh
        if not play_alarm:
            import numpy as np
            data = np.zeros(frame.to_ndarray().shape, dtype=frame.to_ndarray().dtype)
            silent_frame = av.AudioFrame.from_ndarray(data, layout=frame.layout.name, format=frame.format.name)
            silent_frame.sample_rate = frame.sample_rate
            return silent_frame
            
        return audio_handler.process(frame, play_sound=play_alarm)

    ctx = webrtc_streamer(
        key="driver-monitoring",
        mode=WebRtcMode.SENDRECV,
        video_frame_callback=video_frame_callback,
        audio_frame_callback=audio_frame_callback,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"video": True, "audio": True},
        video_html_attrs=VideoHTMLAttributes(autoPlay=True, controls=True, muted=False),
        sendback_audio=True,
    )

    if ctx and not ctx.state.playing:
        with lock:
            shared_bridge["play_alarm"] = False  

with col_main_right:
    st.markdown("### 📜 Nhật Ký Hệ Thống")
    if st.button("Xóa lịch sử", use_container_width=True):
        st.session_state["history"] = []
        with lock:
            shared_bridge["queue_logs"] = []
        st.rerun()
        
    st.write("---")
    
    # Đồng bộ log an toàn từ luồng ngầm lên màn hình hiển thị chính của Streamlit
    with lock:
        if shared_bridge["queue_logs"]:
            for log in shared_bridge["queue_logs"]:
                if log not in st.session_state["history"]:
                    st.session_state["history"].insert(0, log)
            shared_bridge["queue_logs"] = [] # Giải phóng hàng đợi

    if len(st.session_state["history"]) == 0:
        st.info("Chưa ghi nhận sự cố nào trong phiên làm việc này.")
    else:
        for log in st.session_state["history"][:10]:
            st.error(log)