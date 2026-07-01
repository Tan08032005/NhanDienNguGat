import os
import av
import threading
import datetime
import streamlit as st
from streamlit_webrtc import VideoHTMLAttributes, webrtc_streamer, WebRtcMode
from streamlit_autorefresh import st_autorefresh

from drowsy_detection import VideoFrameHandler
from audio_handling import AudioFrameHandler

st.set_page_config(
    page_title="Hệ thống giám sát tài xế thông minh",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    #MainMenu, footer, header { visibility: hidden; }
    .block-container {
        padding-top: 1.5rem !important;
        max-width: 1200px !important;
    }
    .stApp { background-color: #eef1f6 !important; }

    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }
    [data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }

    .sidebar-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 1.25rem;
    }
    .setting-label {
        font-size: 0.92rem;
        font-weight: 600;
        color: #334155;
        margin: 0.75rem 0 0.15rem 0;
    }
    .setting-desc {
        font-size: 0.78rem;
        color: #64748b;
        margin-bottom: 0.25rem;
        line-height: 1.4;
    }
    .value-box {
        background: #dbeafe;
        color: #1d4ed8;
        border-radius: 8px;
        padding: 0.45rem 0.75rem;
        font-size: 0.82rem;
        font-weight: 600;
        text-align: center;
        margin: 0.35rem 0 0.85rem 0;
    }

    .hero-banner {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #6b8cff 100%);
        border-radius: 14px;
        padding: 1.6rem 2rem;
        text-align: center;
        color: white;
        margin-bottom: 1.25rem;
        box-shadow: 0 8px 24px rgba(102, 126, 234, 0.35);
    }
    .hero-banner .hero-icon { font-size: 1.6rem; margin-bottom: 0.35rem; }
    .hero-banner h1 {
        font-size: 1.55rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: 0.3px;
    }
    .hero-banner p {
        font-size: 0.88rem;
        margin: 0.45rem 0 0 0;
        opacity: 0.92;
    }

    .section-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 1.1rem 1.25rem;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.06);
        border: 1px solid #e8edf3;
        margin-bottom: 1rem;
    }
    .section-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #1e293b;
        margin: 0 0 0.85rem 0;
    }

    .status-box {
        background: #fef9c3;
        border: 1px solid #fde68a;
        border-radius: 10px;
        padding: 0.85rem 1rem;
        text-align: center;
    }
    .status-box.active {
        background: #dcfce7;
        border-color: #86efac;
    }
    .status-box.alert {
        background: #fee2e2;
        border-color: #fca5a5;
    }
    .status-icon { font-size: 1.5rem; margin-bottom: 0.25rem; }
    .status-text {
        font-size: 0.92rem;
        font-weight: 600;
        color: #92400e;
        margin: 0;
    }
    .status-box.active .status-text { color: #166534; }
    .status-box.alert .status-text { color: #991b1b; }
    .status-sub {
        font-size: 0.78rem;
        color: #78716c;
        margin: 0.3rem 0 0 0;
    }

    .alert-box {
        background: #fffbeb;
        border: 1px solid #fde68a;
        border-radius: 10px;
        padding: 0.85rem 1rem;
    }
    .alert-box .alert-title {
        font-weight: 600;
        color: #92400e;
        font-size: 0.88rem;
        margin-bottom: 0.5rem;
    }
    .alert-box ul {
        margin: 0;
        padding-left: 1.1rem;
        color: #78716c;
        font-size: 0.8rem;
        line-height: 1.6;
    }

    .stats-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.65rem;
    }
    .stat-item {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.75rem 0.5rem;
        text-align: center;
    }
    .stat-label {
        font-size: 0.72rem;
        color: #64748b;
        margin-bottom: 0.2rem;
    }
    .stat-value {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1e293b;
    }

    .log-item {
        background: #fef2f2;
        border-left: 3px solid #ef4444;
        border-radius: 6px;
        padding: 0.5rem 0.75rem;
        font-size: 0.8rem;
        color: #991b1b;
        margin-bottom: 0.4rem;
    }

    div[data-testid="stSidebar"] div[data-baseweb="slider"] > div:first-child {
        background: #e2e8f0 !important;
    }
    div[data-testid="stSidebar"] div[role="slider"] {
        background-color: #667eea !important;
    }

    .stVideo, iframe { border-radius: 10px; }
</style>
""",
    unsafe_allow_html=True,
)

if "history" not in st.session_state:
    st.session_state["history"] = []

st_autorefresh(interval=1000, limit=10000, key="log_counter")

with st.sidebar:
    st.markdown('<div class="sidebar-title">⚙️ Cài đặt hệ thống</div>', unsafe_allow_html=True)

    st.markdown('<div class="setting-label">👁 Ngưỡng mắt (EAR)</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="setting-desc">Giá trị thấp hơn = nhạy hơn với việc nhắm mắt</div>',
        unsafe_allow_html=True,
    )
    EAR_THRESH = st.slider("EAR", 0.0, 0.4, 0.25, 0.01, label_visibility="collapsed")
    st.markdown(f'<div class="value-box">Giá trị hiện tại: {EAR_THRESH:.2f}</div>', unsafe_allow_html=True)

    st.markdown('<div class="setting-label">⏱ Thời gian chờ</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="setting-desc">Thời gian mắt nhắm trước khi cảnh báo</div>',
        unsafe_allow_html=True,
    )
    WAIT_TIME = st.slider("WAIT", 0.0, 5.0, 1.0, 0.25, label_visibility="collapsed")
    st.markdown(f'<div class="value-box">Giá trị hiện tại: {WAIT_TIME:.1f}s</div>', unsafe_allow_html=True)

    st.markdown('<div class="setting-label">😮 Ngưỡng ngáp (MAR)</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="setting-desc">Giá trị thấp hơn = nhạy hơn với việc ngáp</div>',
        unsafe_allow_html=True,
    )
    MAR_THRESH = st.slider("MAR", 0.0, 1.0, 0.6, 0.05, label_visibility="collapsed")
    st.markdown(f'<div class="value-box">Giá trị hiện tại: {MAR_THRESH:.2f}</div>', unsafe_allow_html=True)

thresholds = {"EAR_THRESH": EAR_THRESH, "WAIT_TIME": WAIT_TIME, "MAR_THRESH": MAR_THRESH}

st.markdown(
    """
<div class="hero-banner">
    <div class="hero-icon">🚗</div>
    <h1>Hệ thống giám sát tài xế thông minh</h1>
    <p>Phát hiện buồn ngủ và ngáp — Đảm bảo an toàn giao thông</p>
</div>
""",
    unsafe_allow_html=True,
)

if "video_handler" not in st.session_state:
    st.session_state["video_handler"] = VideoFrameHandler()
video_handler = st.session_state["video_handler"]

alarm_wav = os.path.join("audio", "wake_up.wav")
audio_handler = AudioFrameHandler(alarm_wav, volume=0.9, loop=False)

lock = threading.Lock()

if "shared_bridge" not in st.session_state:
    st.session_state["shared_bridge"] = {"play_alarm": False, "queue_logs": []}
shared_bridge = st.session_state["shared_bridge"]

col_camera, col_info = st.columns([1.6, 1], gap="medium")

with col_camera:
    st.markdown(
        '<div class="section-card"><div class="section-title">📷 Camera giám sát</div>',
        unsafe_allow_html=True,
    )

    def video_frame_callback(frame: av.VideoFrame):
        img = frame.to_ndarray(format="bgr24")
        img, play_alarm = video_handler.process(img, thresholds)

        with lock:
            if play_alarm and not shared_bridge["play_alarm"]:
                now = datetime.datetime.now().strftime("%H:%M:%S")
                shared_bridge["queue_logs"].append(
                    f"⏱️ [{now}] Cảnh báo: Phát hiện ngủ gật / ngáp!"
                )
            shared_bridge["play_alarm"] = play_alarm

        return av.VideoFrame.from_ndarray(img, format="bgr24")

    def audio_frame_callback(frame: av.AudioFrame):
        with lock:
            play_alarm = shared_bridge["play_alarm"]

        if not play_alarm:
            import numpy as np

            data = np.zeros(frame.to_ndarray().shape, dtype=frame.to_ndarray().dtype)
            silent_frame = av.AudioFrame.from_ndarray(
                data, layout=frame.layout.name, format=frame.format.name
            )
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

    st.markdown("</div>", unsafe_allow_html=True)

with col_info:
    is_playing = ctx.state.playing if ctx else False
    with lock:
        is_alarm = shared_bridge["play_alarm"]

    if is_alarm:
        status_class = "alert"
        status_icon = "🚨"
        status_text = "Cảnh báo nguy hiểm!"
        status_sub = "Phát hiện ngủ gật hoặc ngáp"
    elif is_playing:
        status_class = "active"
        status_icon = "✅"
        status_text = "Đang giám sát"
        status_sub = "Hệ thống hoạt động bình thường"
    else:
        status_class = ""
        status_icon = "💤"
        status_text = "Chờ kết nối"
        status_sub = "Nhấn START để bắt đầu"

    st.markdown(
        f"""
<div class="section-card">
    <div class="section-title">📊 Trạng thái hệ thống</div>
    <div class="status-box {status_class}">
        <div class="status-icon">{status_icon}</div>
        <p class="status-text">{status_text}</p>
        <p class="status-sub">{status_sub}</p>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="section-card">
    <div class="section-title">⚠️ Cảnh báo</div>
    <div class="alert-box">
        <div class="alert-title">🔊 Âm thanh cảnh báo</div>
        <div style="font-size:0.8rem;color:#78716c;margin-bottom:0.4rem;">Sẽ phát khi phát hiện:</div>
        <ul>
            <li>Mắt nhắm quá lâu</li>
            <li>Ngáp liên tục</li>
        </ul>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div class="section-card">
    <div class="section-title">📈 Thông số</div>
    <div class="stats-grid">
        <div class="stat-item">
            <div class="stat-label">EAR ⓘ</div>
            <div class="stat-value">{EAR_THRESH:.2f}</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">MAR ⓘ</div>
            <div class="stat-value">{MAR_THRESH:.2f}</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Thời gian ⓘ</div>
            <div class="stat-value">{WAIT_TIME:.1f}s</div>
        </div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    with lock:
        if shared_bridge["queue_logs"]:
            for log in shared_bridge["queue_logs"]:
                if log not in st.session_state["history"]:
                    st.session_state["history"].insert(0, log)
            shared_bridge["queue_logs"] = []

    if st.session_state["history"]:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📜 Nhật ký sự cố</div>', unsafe_allow_html=True)
        if st.button("Xóa lịch sử", use_container_width=True):
            st.session_state["history"] = []
            st.rerun()
        for log in st.session_state["history"][:5]:
            st.markdown(f'<div class="log-item">{log}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
