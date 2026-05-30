#include "ICM45605.h"
#include <stdio.h>
#include <math.h>

/* --- Filter Configuration Settings --- */
#define SAMPLE_FREQ         25.0f   // Matches the current ICM-45605 ODR (25Hz)
#define FIFO_DT             (1.0f / SAMPLE_FREQ) // Time duration per sample (0.04 seconds)
#define BETA                0.1f    // Filter gain
#define GYRO_SENSITIVITY    131.0f   // Gyro sensitivity (e.g., 16.4 LSB/dps at ±2000dps, 131.0 LSB/dps at ±250dps)
#define DEG_TO_RAD          (3.14159265f / 180.0f)

Quaternion q = {1.0f, 0.0f, 0.0f, 0.0f};

/* --- Function Prototypes --- */
float invSqrt(float x);
void MadgwickAHRSupdateIMU(float gx, float gy, float gz, float ax, float ay, float az, float dt);

// =========================================================================
// ICM45605 Initialization
// =========================================================================
void ICM45605_Init(void) {
    uint8_t dev_id = 0;
    uint8_t data;
    uint8_t read_val;

    printf("\r\n--- ICM-45605 Init Start ---\r\n");

#if defined(MODE_MEASURE_IMU_SLEEP) || defined(MODE_MEASURE_ALL_SLEEP)
    printf(">> Mode: SLEEP CURRENT MEASUREMENT\r\n");
#else
    printf(">> Mode: NORMAL OPERATION\r\n");
#endif

    // 1. Verify WHO_AM_I
    if (HAL_I2C_Mem_Read(&hi2c3, ICM_ADDR, 0x72, 1, &dev_id, 1, 1000) == HAL_OK) {
        printf("[OK] Device ID: 0x%02X\r\n", dev_id);
    }

    // 2. Software Reset
    data = 0x02;
    HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x7F, 1, &data, 1, 1000);
    HAL_Delay(50); // Wait for reset to complete

    // --- [Important] Disable all internal pull-ups (IPREG_BAR region) ---
    data = 0x00;
    HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x7C, 1, &data, 1, 100);
    data = 0x3A;
    HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x7D, 1, &data, 1, 100);
    HAL_I2C_Mem_Read(&hi2c3,  ICM_ADDR, 0x7E, 1, &read_val, 1, 100);
    read_val &= ~(0x40 | 0x08); 
    HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x7E, 1, &read_val, 1, 100);

    data = 0x3B;
    HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x7D, 1, &data, 1, 100);
    HAL_I2C_Mem_Read(&hi2c3,  ICM_ADDR, 0x7E, 1, &read_val, 1, 100);
    read_val &= ~(0x10 | 0x02); 
    HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x7E, 1, &read_val, 1, 100);

#if defined(MODE_MEASURE_IMU_SLEEP) || defined(MODE_MEASURE_ALL_SLEEP)
    // Sleep Mode Configuration for Current Measurement
    data = 0x00; 
    HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x10, 1, &data, 1, 1000);
    data = 0x00;
    HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x54, 1, &data, 1, 1000);
    printf("[OK] Sensors disabled. Entered Sleep Mode.\r\n");

#else
    // Normal Operation Mode Configuration
    // 3. Set ODR (25Hz)
    data = 0x4B;
    HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x1B, 1, &data, 1, 1000); // Accel
    HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x1C, 1, &data, 1, 1000); // Gyro

    // 4. Configure AULP Mode (Indirect Access)
    data = 0x00; HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x7C, 1, &data, 1, 100);
    data = 0x58; HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x7D, 1, &data, 1, 100);
    HAL_I2C_Mem_Read(&hi2c3,  ICM_ADDR, 0x7E, 1, &read_val, 1, 100);
    read_val &= ~(0x10);
    HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x7E, 1, &read_val, 1, 100);

    // 5. Configure Averaging Filter to 1x (Indirect Access)
    data = 0x00; HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x7C, 1, &data, 1, 100);
    data = 0x81; HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x7D, 1, &data, 1, 100);
    HAL_I2C_Mem_Read(&hi2c3,  ICM_ADDR, 0x7E, 1, &read_val, 1, 100);
    read_val &= 0xF0;
    HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x7E, 1, &read_val, 1, 100);

    data = 0x00; HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x7C, 1, &data, 1, 100);
    data = 0xAA; HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x7D, 1, &data, 1, 100);
    HAL_I2C_Mem_Read(&hi2c3,  ICM_ADDR, 0x7E, 1, &read_val, 1, 100);
    read_val &= 0xE1;
    HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x7E, 1, &read_val, 1, 100);

    // 6. Configure FIFO
    data = 0x40; HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x1D, 1, &data, 1, 1000);
    data = 0x07; HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x21, 1, &data, 1, 1000);

    // 7. Enable Power
    data = 0x0A;
    HAL_I2C_Mem_Write(&hi2c3, ICM_ADDR, 0x10, 1, &data, 1, 1000);

    printf("[OK] Sensors enabled. Normal Operation.\r\n");
#endif

    printf("[OK] Init Complete\r\n");
}

// =========================================================================
// ICM45605 Read & Filter Processing
// =========================================================================
void ICM45605_Read_Process(int32_t *ax_mg, int32_t *ay_mg, int32_t *az_mg, int16_t *gx_raw, int16_t *gy_raw, int16_t *gz_raw) {
    uint8_t count_buf[2];
    uint16_t fifo_count = 0;

    if (HAL_I2C_Mem_Read(&hi2c3, ICM_ADDR, 0x12, 1, count_buf, 2, 100) == HAL_OK) {
        fifo_count = (uint16_t)((count_buf[1] << 8) | count_buf[0]);
    }

    if (fifo_count >= 16) {
        uint8_t d[16];
        if (HAL_I2C_Mem_Read(&hi2c3, ICM_ADDR, 0x14, 1, d, 16, 100) == HAL_OK) {
            // --- Extract Raw Data ---
            int16_t raw_ax = (int16_t)((d[2] << 8) | d[1]);
            int16_t raw_ay = (int16_t)((d[4] << 8) | d[3]);
            int16_t raw_az = (int16_t)((d[6] << 8) | d[5]);

            int16_t raw_gx = (int16_t)((d[8] << 8)  | d[7]);
            int16_t raw_gy = (int16_t)((d[10] << 8) | d[9]);
            int16_t raw_gz = (int16_t)((d[12] << 8) | d[11]);

            // Update caller variables for mg and raw outputs
            *ax_mg = (int32_t)raw_ax * 1000 / 16384;
            *ay_mg = (int32_t)raw_ay * 1000 / 16384;
            *az_mg = (int32_t)raw_az * 1000 / 16384;
            *gx_raw = raw_gx;
            *gy_raw = raw_gy;
            *gz_raw = raw_gz;

            // --- Prepare Data for Madgwick Filter ---
            // Gyroscope: Convert from LSB -> dps -> rad/s
            float gx_rad = ((float)raw_gx / GYRO_SENSITIVITY) * DEG_TO_RAD;
            float gy_rad = ((float)raw_gy / GYRO_SENSITIVITY) * DEG_TO_RAD;
            float gz_rad = ((float)raw_gz / GYRO_SENSITIVITY) * DEG_TO_RAD;

            // Accelerometer: Raw values are passed directly because the filter normalizes them, optimizing computation
            float ax_f = (float)raw_ax;
            float ay_f = (float)raw_ay;
            float az_f = (float)raw_az;

            // --- Update Madgwick Filter (introduces MCU computational load) ---
            MadgwickAHRSupdateIMU(gx_rad, gy_rad, gz_rad, ax_f, ay_f, az_f, FIFO_DT);

            // Uncomment the line below to print quaternion values for verification
            // printf("Q - W:%.2f X:%.2f Y:%.2f Z:%.2f\r\n", q.w, q.x, q.y, q.z);
        }
    }
}

// =========================================================================
// Madgwick Filter Core Functions
// =========================================================================

// Fast Inverse Square Root
float invSqrt(float x) {
    float halfx = 0.5f * x;
    float y = x;
    long i = *(long*)&y;
    i = 0x5f3759df - (i >> 1);
    y = *(float*)&i;
    y = y * (1.5f - (halfx * y * y));
    return y;
}

// Madgwick AHRS IMU Update Algorithm
void MadgwickAHRSupdateIMU(float gx, float gy, float gz, float ax, float ay, float az, float dt) {
    float recipNorm;
    float s0, s1, s2, s3;
    float qDot1, qDot2, qDot3, qDot4;
    float _2q0, _2q1, _2q2, _2q3, _4q0, _4q1, _4q2 ,_8q1, _8q2, q0q0, q1q1, q2q2, q3q3;

    // Shorten variable names for readability
    float q0 = q.w;
    float q1 = q.x;
    float q2 = q.y;
    float q3 = q.z;

    // 1. Compute rate of change of quaternion from gyroscope outputs
    qDot1 = 0.5f * (-q1 * gx - q2 * gy - q3 * gz);
    qDot2 = 0.5f * ( q0 * gx + q2 * gz - q3 * gy);
    qDot3 = 0.5f * ( q0 * gy - q1 * gz + q3 * gx);
    qDot4 = 0.5f * ( q0 * gz + q1 * gy - q2 * gx);

    // 2. Compute feedback only if accelerometer measurement is valid (avoids NaN)
    if(!((ax == 0.0f) && (ay == 0.0f) && (az == 0.0f))) {

        recipNorm = invSqrt(ax * ax + ay * ay + az * az);
        ax *= recipNorm;
        ay *= recipNorm;
        az *= recipNorm;

        _2q0 = 2.0f * q0;
        _2q1 = 2.0f * q1;
        _2q2 = 2.0f * q2;
        _2q3 = 2.0f * q3;
        _4q0 = 4.0f * q0;
        _4q1 = 4.0f * q1;
        _4q2 = 4.0f * q2;
        _8q1 = 8.0f * q1;
        _8q2 = 8.0f * q2;
        q0q0 = q0 * q0;
        q1q1 = q1 * q1;
        q2q2 = q2 * q2;
        q3q3 = q3 * q3;

        s0 = _4q0 * q2q2 + _2q2 * ax + _4q0 * q1q1 - _2q1 * ay;
        s1 = _4q1 * q3q3 - _2q3 * ax + 4.0f * q0q0 * q1 - _2q0 * ay - _44q1 + _8q1 * q1q1 + _8q1 * q2q2 + _4q1 * az;
        s2 = 4.0f * q0q0 * q2 + _2q0 * ax + _4q2 * q3q3 - _2q3 * ay - _44q2 + _8q2 * q1q1 + _8q2 * q2q2 + _4q2 * az;
        s3 = 4.0f * q1q1 * q3 - _2q1 * ax + 4.0f * q2q2 * q3 - _2q2 * ay;
        
        recipNorm = invSqrt(s0 * s0 + s1 * s1 + s2 * s2 + s3 * s3);
        s0 *= recipNorm;
        s1 *= recipNorm;
        s2 *= recipNorm;
        s3 *= recipNorm;

        qDot1 -= BETA * s0;
        qDot2 -= BETA * s1;
        qDot3 -= BETA * s2;
        qDot4 -= BETA * s3;
    }

    // 3. Integrate rate of change to compute quaternion
    q0 += qDot1 * dt;
    q1 += qDot2 * dt;
    q2 += qDot3 * dt;
    q3 += qDot4 * dt;

    // 4. Normalize quaternion
    recipNorm = invSqrt(q0 * q0 + q1 * q1 + q2 * q2 + q3 * q3);
    q.w = q0 * recipNorm;
    q.x = q1 * recipNorm;
    q.y = q2 * recipNorm;
    q.z = q3 * recipNorm;
}