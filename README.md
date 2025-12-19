# project1
# DriveGuard - Drowsiness and Driver Presence Detection

DriveGuard is a real-time drowsiness and driver presence detection system that uses computer vision and facial landmark analysis to alert drivers when signs of drowsiness or prolonged absence are detected.

## Features

* **Drowsiness Detection**: Alerts the driver if the eyes remain closed for a critical duration.
* **Driver Absence Detection**: Notifies if the driver is not detected for a prolonged period.
* **Real-time Logging**: Logs all events with timestamps and durations in a structured CSV file.
* **Live Video Feed**: Displays the live camera feed along with real-time driver status updates.
* **User Interface**: Includes a simple, user-friendly graphical interface with status logs and exit controls.

## Installation

Make sure you have Python 3.11.0 installed. Then, clone this repository and install the required libraries:

```bash
pip install -r requirements.txt
```

## Requirements

* opencv-python-headless==4.8.1.78
* numpy==1.25.2
* mediapipe==0.10.4
* scipy==1.11.3
* pillow==10.0.1

## Running the Application

To start the DriveGuard application, simply run:

```bash
python main.py
```

## File Structure

* **driveguard.py**: Main application file.
* **driver\_logs.csv**: Auto-generated log file for storing events.
* **sounds/**: Directory for alert sounds (`alert_sound.wav` and `alert_sound2.wav`).

## How It Works

* **Drowsiness Detection**: Monitors eye aspect ratio (EAR) to detect when the driver’s eyes are closed for a prolonged period.
* **Driver Absence Detection**: Tracks driver presence by continuously checking for face landmarks.
* **Logging**: Logs each detected event (drowsiness, alertness, absence) with timestamps and durations.

## Customization

* Update the `EAR_THRESHOLD` and `CONSECUTIVE_FRAMES` in `driveguard.py` to adjust sensitivity for drowsiness detection.
* Replace the alert sounds in the `sounds/` directory as needed.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Feel free to contribute to this project by submitting a pull request or opening an issue.

## Acknowledgements

* MediaPipe for efficient face mesh detection
* OpenCV for real-time video processing
 
