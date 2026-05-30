# System Firmware

This directory contains the production firmware for the proposed NFC-coupled dual-wearable system.

---

## 1. Ring Firmware (`/ring`)

The firmware for the finger ring device is developed using the official STM32 toolchain.

* **Development Environment**: STM32CubeIDE
* **Target MCU**: STM32U375KGU6
* **Key Middleware / Packages**: **X-CUBE-NFC7** (via STM32CubeMX Middleware & Software Packages)
* **Hardware Components**:
  * `ST25DV64KC`: Dynamic NFC/RFID tag IC (Utilizes the Mailbox feature; Energy Harvesting is not used)
  * `ICM45605`: Low-power 6-axis IMU

### Driver & Hardware Configuration (X-CUBE-NFC7 BSP)
* **ST25DVXXKC GPO PIN**: Configured to `PB0` as `GPIO:EXTI` (HAL_EXTI_DRIVER) for interrupt handling.
* **ST25DVXXKC BUS IO driver**: Configured to `I2C3` (BSP_BUS_DRIVER) for communication with the MCU.
* **ST25DVXXKC LPD PIN**: Configured to `PB1` as `GPIO:Output` for Low Power Mode management.

### Deployment
1. Open the project folder in STM32CubeIDE.
2. For pin connections between the target board and the debugger, please refer to the schematic files under `/Circuit/ring`.
3. To flash the MCU, press and hold the ST-LINK debugger pins directly against the SWD test pads on the ring PCB (SWDIO, SWCLK, GND, VCC).
4. Build the project and flash the binary.

---

## 2. Wristband Firmware (`/wristband`)

The firmware for the wristband module is developed using the PlatformIO ecosystem.

* **Development Environment**: PlatformIO (VS Code extension)
* **Target Board**: Seeed Studio XIAO SAMD21 (`board = seeed_xiao`)
* **Platform**: Atmel SAM (`platform = atmelsam`)
* **Framework**: Arduino (`framework = arduino`)
* **Key Hardware Components & Drivers**:
  * `ST25R3916B`: High-performance NFC universal device / reader IC.
  * Driven by a customized version of the official ST **STSW-ST25RLIB002** library.

### Deployment
1. Open the `/wristband` directory in VS Code with PlatformIO installed.
2. Connect the XIAO SAMD21 module to your PC via a USB Type-C cable.
3. PlatformIO will automatically resolve the core dependencies specified in `platformio.ini`.
4. Click the **Upload** button to build and flash the firmware.