"""
IP Webcam Configuration
Supports multiple camera sources including IP Webcam app for Android/iOS
"""

# IP Webcam Sources Configuration
IP_WEBCAM_SOURCES = {
    "mobile_webcam_1": {
        "name": "Mobile Phone - Main Entrance",
        "enabled": True,
        # IP Webcam app default URL formats:
        "mjpeg_url": "http://192.168.1.108:8080/video",  # MJPEG stream
        "rtsp_url": "rtsp://192.168.1.108:8080/h264_ulaw.sdp",  # RTSP stream (if available)
        "camera_id": "mobile-entrance-1",
        "location": "Main Entrance",
        # Stream settings
        "use_rtsp": False,  # Set to True to use RTSP instead of MJPEG
        "fps_limit": 5,  # Process N frames per second
        "reconnect_delay": 10,  # Seconds to wait before reconnecting
    }
    # "mobile_webcam_2": {
    #     "name": "Mobile Phone - Reception",
    #     "enabled": False,
    #     "mjpeg_url": "http://192.168.1.101:8080/video",
    #     "rtsp_url": "rtsp://192.168.1.101:8080/h264_ulaw.sdp",
    #     "camera_id": "mobile-reception-1",
    #     "location": "Reception Area",
    #     "use_rtsp": False,
    #     "fps_limit": 5,
    #     "reconnect_delay": 10,
    # },
}

# URL Templates for IP Webcam App
# Install "IP Webcam" app on Android from Play Store
# or "IP Camera Lite" on iOS from App Store
IP_WEBCAM_URL_TEMPLATES = {
    "ip_webcam_android": {
        "mjpeg": "http://{ip}:{port}/video",
        "rtsp": "rtsp://{ip}:{port}/h264_ulaw.sdp",
        "jpeg_snapshot": "http://{ip}:{port}/shot.jpg",
        "audio": "http://{ip}:{port}/audio.wav",
    }
    # "ip_camera_lite_ios": {
    #     "mjpeg": "http://{ip}:{port}/live",
    #     "rtsp": "rtsp://{ip}:{port}/live.sdp",
    #     "jpeg_snapshot": "http://{ip}:{port}/snapshot.jpg",
    # },
}

def get_active_webcam_sources():
    """Get list of enabled webcam sources"""
    return {
        key: config
        for key, config in IP_WEBCAM_SOURCES.items()
        if config.get("enabled", False)
    }

def get_stream_url(source_name: str) -> str:
    """Get the appropriate stream URL for a source"""
    if source_name not in IP_WEBCAM_SOURCES:
        raise ValueError(f"Unknown webcam source: {source_name}")
    
    config = IP_WEBCAM_SOURCES[source_name]
    
    if config.get("use_rtsp", False):
        return config.get("rtsp_url")
    else:
        return config.get("mjpeg_url")
