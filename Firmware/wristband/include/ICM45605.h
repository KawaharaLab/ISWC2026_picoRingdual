#ifndef ICM45605_H
#define ICM45605_H

#include <Arduino.h>
#include <Wire.h>

#define ICM_ADDR 0x68 // AD0の接続状況により0x69の場合があります

// 関数宣言
void ICM45605_Init(TwoWire &w);
void ICM45605_Read_Process(int32_t *ax_mg, int32_t *ay_mg, int32_t *az_mg, int16_t *gx_raw, int16_t *gy_raw, int16_t *gz_raw);

#endif