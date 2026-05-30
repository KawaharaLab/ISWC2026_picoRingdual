#ifndef ICM45605_H
#define ICM45605_H

#include "main.h" // Change accordingly depending on the series being used

// I2C Configuration
extern I2C_HandleTypeDef hi2c3;
#define ICM_ADDR 0xD0

/* --- Definition of Quaternion Structure --- */
typedef struct {
    float w;
    float x;
    float y;
    float z;
} Quaternion;

/* --- "Declaration" of Global Variables (Instance is not created here) --- */
extern Quaternion q;

// Initialization function
void ICM45605_Init(void);
// Read function (Pass pointers as arguments to receive the results)
void ICM45605_Read_Process(int32_t *ax_mg, int32_t *ay_mg, int32_t *az_mg, int16_t *gx, int16_t *gy, int16_t *gz);

#endif