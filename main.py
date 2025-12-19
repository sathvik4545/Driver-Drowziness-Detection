import cv2
import time
import numpy as np
import mediapipe as mp
from scipy.spatial import distance
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import mysql.connector
import requests
import pygame
import threading

# -----------------------------
# Initialize pygame mixer for sounds
# -----------------------------
pygame.mixer.init()

def play_sound(file_path):
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play(-1)  # Loop until stopped

def stop_sound():
    pygame.mixer.music.stop()

# -----------------------------
# MediaPipe Face Mesh Setup
# -----------------------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True,
                                  min_detection_confidence=0.7, min_tracking_confidence=0.7)

# -----------------------------
# MySQL Connection
# -----------------------------
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="driveguard"
)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME,
    event_type VARCHAR(50),
    details VARCHAR(255),
    duration_seconds FLOAT,
    latitude DOUBLE DEFAULT NULL,
    longitude DOUBLE DEFAULT NULL,
    location VARCHAR(255) DEFAULT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    start_time DATETIME,
    end_time DATETIME,
    duration_seconds FLOAT,
    total_frames INT,
    normal_frames INT,
    drowsy_alerts INT,
    absent_alerts INT,
    accuracy FLOAT
)
""")

# -----------------------------
# GPS Function
# -----------------------------
def get_gps_location():
    try:
        response = requests.get("http://ip-api.com/json/")
        data = response.json()
        if data['status'] == 'success':
            lat = data.get('lat', None)
            lon = data.get('lon', None)
            loc = f"{data.get('city', '')}, {data.get('regionName', '')}, {data.get('country', '')}"
            return lat, lon, loc
    except Exception as e:
        print("Error fetching GPS location:", e)
    return None, None, None

cached_lat, cached_lon, cached_loc = get_gps_location()

# -----------------------------
# Event Logging
# -----------------------------
def log_event(event_type, details, start_time=None, end_time=None):
    timestamp = datetime.now()
    duration = round(end_time - start_time, 2) if start_time and end_time else 0.0
    cursor.execute(
        "INSERT INTO logs (timestamp, event_type, details, duration_seconds, latitude, longitude, location) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (timestamp, event_type, details, duration, cached_lat, cached_lon, cached_loc)
    )
    conn.commit()
    log_table.insert("", "end", values=(
        timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        event_type, details, duration,
        f"{cached_lat:.4f}" if cached_lat else "N/A",
        f"{cached_lon:.4f}" if cached_lon else "N/A",
        cached_loc if cached_loc else "N/A"
    ))

# -----------------------------
# Eye Aspect Ratio
# -----------------------------
def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)

# -----------------------------
# Detection Thresholds
# -----------------------------
EAR_THRESHOLD = 0.25
CONSECUTIVE_FRAMES = 20
MISSING_FACE_FRAMES = 30

frame_count = 0
missing_frame_count = 0
drowsy = False
driver_absent = False
drowsiness_start_time = None
absence_start_time = None

# -----------------------------
# Session Counters
# -----------------------------
session_start_time = time.time()
total_frames = 0
normal_frames = 0
drowsy_alerts = 0
absent_alerts = 0

# -----------------------------
# Tkinter GUI Setup
# -----------------------------
root = tk.Tk()
root.title("DriveGuard - Drowsiness Detection")
root.geometry("1300x950")
root.configure(bg="#f0f0f0")

alert_text = tk.StringVar()
ear_text = tk.StringVar(value="EAR: -")

header = tk.Label(root, text="DriveGuard - Drowsiness Detection System",
                  font=("Helvetica", 18, "bold"), bg="#1d3557", fg="white", pady=10)
header.pack(fill=tk.X)

video_label = tk.Label(root, bg="#333333")
video_label.pack(pady=10)

# -----------------------------
# Info Frame
# -----------------------------
info_frame = tk.Frame(root, bg="#f0f0f0")
info_frame.pack(pady=10)

ear_label = tk.Label(info_frame, textvariable=ear_text, font=("Helvetica", 14), bg="#f0f0f0", fg="blue")
ear_label.pack(side=tk.LEFT, padx=20)

alert_label = tk.Label(info_frame, textvariable=alert_text, font=("Helvetica", 16, "bold"), bg="#f0f0f0", fg="red")
alert_label.pack(side=tk.LEFT, padx=20)

def show_summary():
    global session_start_time, total_frames, normal_frames, drowsy_alerts, absent_alerts
    session_end_time = time.time()
    duration_sec = round(session_end_time - session_start_time, 2)
    accuracy = round((normal_frames / total_frames) * 100, 2) if total_frames else 0.0

    cursor.execute(
        "INSERT INTO sessions (start_time, end_time, duration_seconds, total_frames, normal_frames, drowsy_alerts, absent_alerts, accuracy) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (datetime.fromtimestamp(session_start_time), datetime.fromtimestamp(session_end_time), duration_sec,
         total_frames, normal_frames, drowsy_alerts, absent_alerts, accuracy)
    )
    conn.commit()

    summary = f"""
========= DRIVEGUARD SESSION SUMMARY =========
Start Time      : {datetime.fromtimestamp(session_start_time)}
End Time        : {datetime.fromtimestamp(session_end_time)}
Duration        : {int(duration_sec//60)} min {int(duration_sec%60)} sec
Total Frames    : {total_frames}
Normal Frames   : {normal_frames}
Drowsy Alerts   : {drowsy_alerts}
Absent Alerts   : {absent_alerts}
System Accuracy : {accuracy} %
==============================================
"""
    print(summary)
    messagebox.showinfo("Session Summary", summary)

def end_session():
    global running
    running = False
    root.after(100, show_summary)

end_button = tk.Button(info_frame, text="End Session", command=end_session,
                       bg="#e63946", fg="white", font=("Helvetica", 14), width=15)
end_button.pack(side=tk.LEFT, padx=20)

exit_button = tk.Button(info_frame, text="Exit", command=root.quit,
                        bg="#a8dadc", fg="black", font=("Helvetica", 14), width=15)
exit_button.pack(side=tk.LEFT, padx=20)

# -----------------------------
# Log Table
# -----------------------------
table_outer_frame = tk.Frame(root, bg="black")
table_outer_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

columns = ("Timestamp", "Event Type", "Details", "Duration (Seconds)", "Latitude", "Longitude", "Location")
log_table = ttk.Treeview(table_outer_frame, columns=columns, show="headings", height=10)
style = ttk.Style()
style.theme_use("default")
style.configure("Treeview", background="white", foreground="black", rowheight=30, font=("Helvetica", 12))
style.configure("Treeview.Heading", background="#d9d9d9", foreground="black", font=("Helvetica", 14, "bold"))
for col in columns:
    log_table.heading(col, text=col, anchor="center")
    log_table.column(col, anchor="center", width=180, stretch=False)
scrollbar = ttk.Scrollbar(table_outer_frame, orient="vertical", command=log_table.yview)
log_table.configure(yscroll=scrollbar.set)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
log_table.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

# -----------------------------
# Video Capture & Detection
# -----------------------------
cap = cv2.VideoCapture(0)
running = True

def start_detection():
    global frame_count, missing_frame_count, drowsy, driver_absent, drowsiness_start_time, absence_start_time
    global total_frames, normal_frames, drowsy_alerts, absent_alerts

    if not running:
        return

    ret, frame = cap.read()
    if not ret:
        root.after(40, start_detection)
        return

    total_frames += 1
    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(cv2.resize(frame, (640, 480)), cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    if results.multi_face_landmarks:
        if driver_absent:
            driver_absent = False
            if absence_start_time:
                absence_end_time = time.time()
                log_event("Driver Presence", "Driver detected again", absence_start_time, absence_end_time)
            video_label.configure(bg="#333333")
            alert_text.set("")

        missing_frame_count = 0

        for face_landmarks in results.multi_face_landmarks:
            ih, iw, _ = frame.shape
            left_eye = [(face_landmarks.landmark[i].x * iw, face_landmarks.landmark[i].y * ih)
                        for i in [362, 385, 387, 263, 373, 380]]
            right_eye = [(face_landmarks.landmark[i].x * iw, face_landmarks.landmark[i].y * ih)
                         for i in [33, 160, 158, 133, 153, 144]]
            ear = (eye_aspect_ratio(left_eye) + eye_aspect_ratio(right_eye)) / 2.0
            ear_text.set(f"EAR: {ear:.3f}")

            if ear < EAR_THRESHOLD:
                frame_count += 1
                if frame_count >= CONSECUTIVE_FRAMES:
                    if not drowsy:
                        drowsy = True
                        drowsiness_start_time = time.time()
                        drowsy_alerts += 1
                        log_event("Drowsiness", "Driver is drowsy", drowsiness_start_time)
                        alert_text.set("⚠️ DRIVER DROWSY!")
                        video_label.configure(bg="#ff4d4d")
                        play_sound("sounds/alert_sound.wav")
                        messagebox.showwarning("DriveGuard Alert", "⚠️ DRIVER DROWSY! Please stay alert.")
                        stop_sound()
            else:
                if drowsy:
                    drowsiness_end_time = time.time()
                    log_event("Alert", "Driver awake", drowsiness_start_time, drowsiness_end_time)
                    alert_text.set("")
                    video_label.configure(bg="#333333")
                    drowsy = False
                frame_count = 0
                normal_frames += 1

    else:
        missing_frame_count += 1
        if missing_frame_count >= MISSING_FACE_FRAMES:
            if not driver_absent:
                driver_absent = True
                absence_start_time = time.time()
                absent_alerts += 1
                log_event("Driver Absence", "Driver not detected", absence_start_time)
                alert_text.set("🚫 DRIVER NOT DETECTED!")
                video_label.configure(bg="#ffcc00")
                play_sound("sounds/alert_sound2.wav")
                messagebox.showinfo("DriveGuard Alert", "🚫 DRIVER NOT DETECTED!")
                stop_sound()

    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    imgtk = ImageTk.PhotoImage(image=img)
    video_label.imgtk = imgtk
    video_label.configure(image=imgtk)

    root.after(40, start_detection)

# -----------------------------
# Start Detection
# -----------------------------
start_detection()
root.mainloop()

# Cleanup
cap.release()
conn.close()
