# BLE Baseline Evaluation Firmware

This directory contains the Bluetooth Low Energy (BLE) firmware used as the baseline for energy efficiency comparisons against our proposed NFC-based architecture.

## Overview

The BLE baseline system implements a high-frequency (20Hz) IMU data streaming pipeline optimized for short-range, low-power operation between two Seeed Studio XIAO nRF52840 modules:
* **Peripheral Node (Ring/Sensor side)**: Reads ICM-45605 IMU data, computes quaternions via a Madgwick filter, compresses the data, and transmits it.
* **Central Node (Receiver/PC side)**: Automatically scans, connects, subscribes to notifications, and streams data over Serial.

---

## Technical Specifications & Optimizations

### 1. BLE Protocol Optimization
* **Transmission Scheme**: BLE **Notify** mechanism. This eliminates round-trip request overhead, minimizing packet loss and power consumption compared to Read operations.
* **RF Tx Power**: Set to the absolute minimum of **-40dBm** (`NRF_RADIO->TXPOWER = 0x28`), leveraging the proximity (approx. 15cm) of the dual-wearable setup.
* **Connection Interval**: Synchronized exactly to the IMU data generation rate at **50ms (20Hz)** using `BLE.setConnectionInterval(40, 40)`. This prevents redundant polling and allows the radio to sleep immediately after transmission.

### 2. Data Packet Structure
To minimize payload size and transmission time, 32-bit float orientation data is compressed into a **9-byte packet**:
* `[0-7] Bytes`: Quaternion ($W, X, Y, Z$) represented as four `int16_t` integers (scaled by $30000.0f$).
* `[8] Byte`: GPIO / Button status bits.

---

## Development Environment Setup

### Prerequisites
* **IDE**: Arduino IDE
* **Core**: **Seeed nRF52 mbed-enabled Boards** (Mandatory)
  * *Note: Do not use the non-mbed version ("Seeed nRF52 Boards"), as it causes permission and Python encoding (`adafruit-nrfutil`) errors on macOS.*
* **Libraries**:
  * `ArduinoBLE` (Official Arduino Library)
  * `Wire` (Built-in for I2C communication)

### Target Board Configuration in Arduino IDE
* Board Selection: `Seeed nRF52 mbed-enabled Boards` -> **`XIAO nRF52840 Sense`** (or `XIAO nRF52840`)

---

## Deployment

1. **Flash Peripheral Node**: Open `ring_demo/ring_demo.ino`, select the target port, and upload.
2. **Flash Central Node**: Open `receiver_demo/receiver_demo.ino`, select the target port, and upload.
3. **Verification**: Connect the Central Node to a PC. It will automatically pair with the Peripheral. Open the Serial Monitor to verify the incoming data formatted as: `IMU:w,x,y,z,gpio`.