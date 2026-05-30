# GUI Applications

This directory contains the demonstration and visualization applications for the *picoRing dual* system. Desktop-heavy interactive tools are implemented in Python, while productivity and utility tools are built as web-based applications.

---

## Application Directory

### 1. Game Application (`/game`)
* **Environment**: Python 3.11+
* **Primary Script**: `pico_sniper.py` (complemented by `main.py`, `youtube_mode.py`, and `serial_input.py`)
* **Description**: A 3D application leveraging a custom ModernGL-based engine (`/mgllib`) with two selectable modes via an interactive menu:
  * **Video Mode**: Supports playback, pausing, and skipping of video files.
  * **Game Mode**: Enables a dual-handed controls interface (aiming and reloading via the right hand, and locomotion/movement via the left hand).

### 2. 3D Viewer (`/3d_viewer`)
* **Environment**: Python 3.11+
* **Primary Script**: `3D_viewer.py`
* **Description**: Provides a real-time 3D desktop dashboard using telemetry data from both hands' trackballs and IMU sensors. It animates 3D models of the rings and moving trackball icons to intuitively mirror user input.

### 3. Sensor Viewer (`/sensor_viewer`)
* **Environment**: Python 3.11+
* **Primary Script**: `sensor_viewer.py`
* **Description**: Reads data from the hardware via serial communication to plot and display raw real-time stream data from the trackball and the IMU quaternion outputs.

### 4. Map Tracker (`/map`)
* **Environment**: Web-based (JavaScript / Web Serial API)
* **Primary Entrypoint**: `index.html` (supported by `app.js`, `map.js`, `menu.js`, and `serial.js`)
* **Description**: Allows users to select predefined routes from a menu and display them on a map interface. The map supports panning, scrolling, and zooming actions bound to the trackball inputs.
* **Prerequisite**: Requires a valid Google Maps JavaScript API key configured in the application environment.

### 5. Email Client Demo (`/email`)
* **Environment**: Web-based (JavaScript / HTML5)
* **Primary Entrypoint**: `email.html`
* **Description**: Simulates a productivity application allowing selection of emails from an inbox view and smooth scrolling through the message bodies via wearable inputs.

### 6. Cooking Assistant (`/cooking`)
* **Environment**: Web-based (JavaScript / HTML5)
* **Primary Entrypoint**: `cooking.html`
* **Description**: A contextual monitoring tool tracking user activity. It processes IMU telemetry and triggers an on-screen warning alert if the user's hands stop moving for a set duration.

---

## Requirements & Execution

### Running Python Applications

Navigate to the respective directory, install the required dependencies, and launch the script:

**Game Application:**
```bash
cd game
pip install -r requirements.txt
python pico_sniper.py
```

**3D Viewer:**
```bash
cd 3d_viewer
python 3D_viewer.py
```

**Sensor Viewer:**
```bash
cd sensor_viewer
python sensor_viewer.py
```

### Running Web Applications (`/map`, `/email`, `/cooking`)

1. Navigate to the target application folder.
2. Start a local HTTP server using Python:
```bash
cd map
python -m http.server 8000
```
3. Open a Chromium-based browser (such as Google Chrome or Microsoft Edge) that natively supports the **Web Serial API**, and navigate to `http://localhost:8000`.
