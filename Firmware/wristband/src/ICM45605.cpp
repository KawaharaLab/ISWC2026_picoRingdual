#include "ICM45605.h"

static TwoWire *_wire;

// Helper: Register write
void writeReg(uint8_t reg, uint8_t data) {
    _wire->beginTransmission(ICM_ADDR);
    _wire->write(reg);
    _wire->write(data);
    _wire->endTransmission();
}

// Helper: Register read
void readRegs(uint8_t reg, uint8_t *buffer, uint8_t len) {
    _wire->beginTransmission(ICM_ADDR);
    _wire->write(reg);
    _wire->endTransmission(false);
    _wire->requestFrom((uint8_t)ICM_ADDR, len);
    for (uint8_t i = 0; i < len; i++) {
        if (_wire->available()) buffer[i] = _wire->read();
    }
}

void ICM45605_Init(TwoWire &w) {
    _wire = &w;
    uint8_t dev_id = 0;
    uint8_t read_val;

    Serial.println("\r\n--- ICM-45605 Init Start ---");

    // 1. Check WHO_AM_I (0x72)
    readRegs(0x72, &dev_id, 1);
    Serial.print("[OK] Device ID: 0x");
    Serial.println(dev_id, HEX);

    // 2. Soft Reset
    writeReg(0x7F, 0x02);
    delay(50);

    // --- Disable Internal Pull-ups (IPREG_BAR) ---
    writeReg(0x7C, 0x00);
    writeReg(0x7D, 0x3A);
    readRegs(0x7E, &read_val, 1);
    writeReg(0x7E, read_val & ~(0x40 | 0x08));

    writeReg(0x7D, 0x3B);
    readRegs(0x7E, &read_val, 1);
    writeReg(0x7E, read_val & ~(0x10 | 0x02));

#if defined(MODE_MEASURE_IMU_SLEEP)
    writeReg(0x10, 0x00); // PWR_MGMT0
    writeReg(0x54, 0x00); // PWR_MGMT_AUX1
    Serial.println("[OK] Entered Sleep Mode.");
#else
    // 3. ODR Configuration (25Hz)
    writeReg(0x1B, 0x4B); 
    writeReg(0x1C, 0x4B);

    // 4. AULP Mode
    writeReg(0x7C, 0x00);
    writeReg(0x7D, 0x58);
    readRegs(0x7E, &read_val, 1);
    writeReg(0x7E, read_val & ~0x10);

    // 5. Averaging Filter (Accel: 0x81, Gyro: 0xAA)
    writeReg(0x7D, 0x81);
    readRegs(0x7E, &read_val, 1);
    writeReg(0x7E, read_val & 0xF0);

    writeReg(0x7D, 0xAA);
    readRegs(0x7E, &read_val, 1);
    writeReg(0x7E, read_val & 0xE1);

    // 6. FIFO Configuration
    writeReg(0x1D, 0x40);
    writeReg(0x21, 0x07);

    // 7. Enable Power (Low Power/Low Noise)
    writeReg(0x10, 0x0A);
    Serial.println("[OK] Sensors enabled. Normal Operation.");
#endif
    Serial.println("[OK] Init Complete");
}

void ICM45605_Read_Process(int32_t *ax_mg,