# picoRing *dual*

This repository contains the hardware design files, firmware, and evaluation applications for the dual-wearable system (Finger Ring and Wristband) presented in our ISWC 2026 paper.

---

## Repository Structure

The project consists of four main modules:

### 1. BLE (`/BLE`)
Contains the firmware used for baseline evaluation.
* **`ring_demo/` / `receiver_demo/`**: Firmware implemented to benchmark power consumption when the ring and wristband communicate via Bluetooth Low Energy (BLE) instead of NFC.

### 2. Circuit (`/Circuit`)
Contains the hardware design files created with KiCad (v7 or later).
* **`ring/`**: Schematic and PCB layout files for the finger-worn ring node.
* **`wristband/`**: Schematic and PCB layout files for the wristband module.

### 3. Firmware (`/Firmware`)
Contains the source code for the proposed NFC-coupled system.
* **`ring/`**: STM32CubeIDE project for the STM32U375KGUx MCU embedded in the ring, including drivers for the `ICM45605` IMU and `ST25DVxxKC` NFC tag.
* **`wristband/`**: PlatformIO project for the Seeed Studio XIAO based wristband, utilizing the ST `NFC-RFAL` library for NFC polling.

### 4. GUI (`/GUI`)
Contains the following applications for system demonstration and data visualization:
* **`sensor_viewer/`**: Displays raw data from the trackball and IMU quaternion outputs.
* **`3d_viewer/`**: Visualizes data from both hands' trackballs and IMU sensors to dynamically control 3D models of the ring and trackball icons.
* **`map/`**: A web-based application that displays routes selected from a menu. Supports map scrolling and zooming via the trackball (Requires a Google Maps API key).
* **`game/`**: A 3D application with two selectable modes via a menu:
  * **Video Mode**: Supports playback, pausing, and skipping of videos.
  * **Game Mode**: Enables aiming and reloading with the right hand, and locomotion with the left hand.
* **`email/`**: Supports email selection and message body scrolling.
* **`cooking/`**: Detects hand movements via the IMU and triggers a warning alert if the hand stops moving for a specific duration.