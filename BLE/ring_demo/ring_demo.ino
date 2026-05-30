#include <ArduinoBLE.h>
#include <Wire.h>
#include <string.h>

// ==========================================
// 🛠️ 測定モード切り替え設定 (ここを書き換える)
// 1: XIAO起動のみ (IMUスリープ、BLE停止)
// 2: XIAO + IMU計算のみ (BLE停止)
// 3: XIAO + IMU + BLE送信 (フル機能・低電力化適用)
// 4: XIAO + BLE送信のみ [ダミー送信] (IMUスリープ)
// ==========================================
#define MEASURE_MODE 4

/* --- ICM45605 設定値 --- */
#define ICM_ADDR            0x68 
#define SAMPLE_FREQ         25.0f   
#define FIFO_DT             (1.0f / SAMPLE_FREQ) 
#define BETA                0.1f    
#define GYRO_SENSITIVITY    131.0f   
#define DEG_TO_RAD          (3.14159265f / 180.0f)

struct Quaternion { float w, x, y, z; };
Quaternion q = {1.0f, 0.0f, 0.0f, 0.0f};

/* --- BLE 設定 --- */
BLEService imuService("19B10000-E8F2-537E-4F6C-D104768A1214");
BLECharacteristic imuCharacteristic("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify, 9);

/* プロトタイプ宣言 */
void I2C_WriteByte(uint8_t reg, uint8_t data);
uint8_t I2C_ReadByte(uint8_t reg);
void I2C_ReadBytes(uint8_t reg, uint8_t *buffer, uint8_t length);
void ICM45605_Init(void);
void ICM45605_EnterDeepSleep(void); 
bool ICM45605_Read_Process(int32_t *ax_mg, int32_t *ay_mg, int32_t *az_mg, int16_t *gx_raw, int16_t *gy_raw, int16_t *gz_raw);
float invSqrt(float x);
void MadgwickAHRSupdateIMU(float gx, float gy, float gz, float ax, float ay, float az, float dt);

// =========================================================================
// Setup
// =========================================================================
void setup() {
  Serial.begin(9600);
  
  // PC接続を最大3秒待つ（ログの頭欠け防止 ＆ バッテリー単体測定対応）
  unsigned long startWait = millis();
  while (!Serial && (millis() - startWait < 3000)) {
    delay(10);
  }

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH); 

  Serial.println("\r\n=================================");
  Serial.print("  POWER MEASUREMENT MODE: ");
  Serial.println(MEASURE_MODE);
  Serial.println("=================================");

  // ----------------------------------------------------
  // 【モード1】XIAO起動のみの場合
  // ----------------------------------------------------
  #if (MEASURE_MODE == 1)
    Wire.begin();
    ICM45605_EnterDeepSleep(); 
    Serial.println("[OK] Mode 1 Initialized. System entered deep sleep.");
  
  // ----------------------------------------------------
  // 【モード2】XIAO + IMU計算のみの場合
  // ----------------------------------------------------
  #elif (MEASURE_MODE == 2)
    Serial.println("[MODE 2] IMU Active. BLE disabled.");
    Wire.begin();
    ICM45605_Init();

  // ----------------------------------------------------
  // 【モード3】フル機能 (XIAO + IMU + BLE送信) の場合
  // ----------------------------------------------------
  #elif (MEASURE_MODE == 3)
    Serial.println("[MODE 3] Full Connection Mode (IMU + BLE).");
    Wire.begin();
    ICM45605_Init();

    if (!BLE.begin()) {
      Serial.println("BLE Init Failed!");
      while (1);
    }
    //NRF_RADIO->TXPOWER = 0x28;  
    //NRF_RADIO->TXPOWER = 0x00; // 0dBm (0x00)  
    NRF_RADIO->TXPOWER = 0xF4; // -12dBm (2の補数表現で 0xF4)         
    BLE.setConnectionInterval(40, 40); 

    BLE.setLocalName("XIAO_IMU_A");
    BLE.setAdvertisedService(imuService);
    imuService.addCharacteristic(imuCharacteristic);
    BLE.addService(imuService);

    uint8_t initPacket[9] = {0};
    int16_t initialW = 1.0f * 30000.0f;
    memcpy(&initPacket[0], &initialW, 2);
    imuCharacteristic.writeValue(initPacket, 9);
    BLE.advertise();

  // ----------------------------------------------------
  // 【モード4】BLE送信のみ [ダミー送信]
  // ----------------------------------------------------
  #elif (MEASURE_MODE == 4)
    Serial.println("[MODE 4] BLE Active (Dummy Data) & IMU Deep Sleep.");
    Wire.begin();
    ICM45605_EnterDeepSleep(); 

    if (!BLE.begin()) {
      Serial.println("BLE Init Failed!");
      while (1);
    }
    //NRF_RADIO->TXPOWER = 0x28; // -40dBm 
    //NRF_RADIO->TXPOWER = 0x00; // 0dBm (0x00)  
    NRF_RADIO->TXPOWER = 0xF4; // -12dBm (2の補数表現で 0xF4)  
    BLE.setConnectionInterval(40, 40);

    BLE.setLocalName("XIAO_IMU_A");
    BLE.setAdvertisedService(imuService);
    imuService.addCharacteristic(imuCharacteristic);
    BLE.addService(imuService);

    uint8_t initPacket[9] = {0};
    imuCharacteristic.writeValue(initPacket, 9);
    BLE.advertise();
    Serial.println("BLE Advertising Started (Dummy Mode)...");
  #endif
}

// =========================================================================
// Loop
// =========================================================================
void loop() {
  // ----------------------------------------------------
  // 【モード1】50ms休止するだけ
  // ----------------------------------------------------
  #if (MEASURE_MODE == 1)
    delay(50);
  
  // ----------------------------------------------------
  // 【モード2】50ms周期でIMUを叩いてフィルタ計算
  // ----------------------------------------------------
  #elif (MEASURE_MODE == 2)
    int32_t ax, ay, az;
    int16_t gx, gy, gz;
    ICM45605_Read_Process(&ax, &ay, &az, &gx, &gy, &gz);
    delay(50);

  // ----------------------------------------------------
  // 【モード3】フル機能 (接続中、50ms周期で計算＆送信)
  // ----------------------------------------------------
  #elif (MEASURE_MODE == 3)
    BLEDevice central = BLE.central();
    if (central) {
      Serial.print("Connected to: ");
      Serial.println(central.address());
      //digitalWrite(LED_BUILTIN, LOW);

      while (central.connected()) {
        int32_t ax, ay, az;
        int16_t gx, gy, gz;
        
        if (ICM45605_Read_Process(&ax, &ay, &az, &gx, &gy, &gz)) {
          uint8_t sendPacket[9];
          int16_t w_raw = (int16_t)(q.w * 30000.0f);
          int16_t x_raw = (int16_t)(q.x * 30000.0f);
          int16_t y_raw = (int16_t)(q.y * 30000.0f);
          int16_t z_raw = (int16_t)(q.z * 30000.0f);
          uint8_t gpio_byte = 0; 

          int idx = 0;
          memcpy(&sendPacket[idx], &w_raw, 2); idx += 2;
          memcpy(&sendPacket[idx], &x_raw, 2); idx += 2;
          memcpy(&sendPacket[idx], &y_raw, 2); idx += 2;
          memcpy(&sendPacket[idx], &z_raw, 2); idx += 2;
          sendPacket[idx] = gpio_byte;

          imuCharacteristic.writeValue(sendPacket, 9);
        }
        delay(50); // 送信後にきっちり50ms待機
      }
      Serial.println("Disconnected.");
      digitalWrite(LED_BUILTIN, HIGH);
    }

  // ----------------------------------------------------
  // 【モード4】ダミー送信 (接続中、50ms周期で固定値送信)
  // ----------------------------------------------------
  #elif (MEASURE_MODE == 4)
    BLEDevice central = BLE.central();
    if (central) {
      Serial.print("Connected to: ");
      Serial.println(central.address());
      //digitalWrite(LED_BUILTIN, LOW); 
      uint8_t d_gpio = 0x00; 

      while (central.connected()) {
        uint8_t dummyPacket[9];
        int16_t dw = (int16_t)(1.0f * 30000.0f);
        int16_t dx = 0; int16_t dy = 0; int16_t dz = 0;
        d_gpio += 1;

        int idx = 0;
        memcpy(&dummyPacket[idx], &dw, 2); idx += 2;
        memcpy(&dummyPacket[idx], &dx, 2); idx += 2;
        memcpy(&dummyPacket[idx], &dy, 2); idx += 2;
        memcpy(&dummyPacket[idx], &dz, 2); idx += 2;
        dummyPacket[idx] = d_gpio;

        imuCharacteristic.writeValue(dummyPacket, 9);
        
        delay(50); // 送信後にきっちり50ms待機
      }
      Serial.println("Disconnected.");
      digitalWrite(LED_BUILTIN, HIGH);
    }
  #endif
}

// =========================================================================
// 🔄 【HALからの移植】ICM45605 徹底スリープ関数
// =========================================================================
void ICM45605_EnterDeepSleep(void) {
    uint8_t dev_id = 0;
    uint8_t read_val;

    Serial.println("\r\n--- ICM-45605 Deep Sleep Start ---");

    // 1. WHO_AM_I 確認
    dev_id = I2C_ReadByte(0x72);
    Serial.print("[OK] Device ID: 0x");
    Serial.println(dev_id, HEX);

    // 2. ソフトリセット
    I2C_WriteByte(0x7F, 0x02);
    delay(50); 

    // --- 内部プルアップの全解除 (IPREG_BAR 領域) ---
    // Bank 0x00, Address 0x3A (AP_CS, AP_SCLK)
    I2C_WriteByte(0x7C, 0x00);
    I2C_WriteByte(0x7D, 0x3A);
    read_val = I2C_ReadByte(0x7E);
    read_val &= ~(0x40 | 0x08); // bit6: SCLK(SCL), bit3: CS をOFF
    I2C_WriteByte(0x7E, read_val);

    // Bank 0x00, Address 0x3B (AP_SDO, AP_SDI)
    I2C_WriteByte(0x7D, 0x3B);
    read_val = I2C_ReadByte(0x7E);
    read_val &= ~(0x10 | 0x02); // bit4: SDO(AD0), bit1: SDI(SDA) をOFF
    I2C_WriteByte(0x7E, read_val);

    // PWR_MGMT0 (0x10): GYRO_MODE=00(OFF), ACCEL_MODE=00(OFF)
    I2C_WriteByte(0x10, 0x00);

    // PWR_MGMT_AUX1 (0x54): 補助インターフェースも確実にOFFにする
    I2C_WriteByte(0x54, 0x00);

    Serial.println("[OK] Sensors & AUX disabled. Internal pull-ups cleared.");
}

// =========================================================================
// I2C 読み書き用ヘルパー関数
// =========================================================================
void I2C_WriteByte(uint8_t reg, uint8_t data) {
  Wire.beginTransmission(ICM_ADDR);
  Wire.write(reg);
  Wire.write(data);
  Wire.endTransmission();
}

uint8_t I2C_ReadByte(uint8_t reg) {
  Wire.beginTransmission(ICM_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(ICM_ADDR, 1);
  return Wire.read();
}

void I2C_ReadBytes(uint8_t reg, uint8_t *buffer, uint8_t length) {
  Wire.beginTransmission(ICM_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(ICM_ADDR, length);
  for (uint8_t i = 0; i < length; i++) {
    if (Wire.available()) {
      buffer[i] = Wire.read();
    }
  }
}

// =========================================================================
// ICM45605 通常初期化
// =========================================================================
void ICM45605_Init(void) {
    uint8_t read_val;

    // 通常起動時も、まずはプルアップ解除を施して漏れ電流をカット
    I2C_WriteByte(0x7C, 0x00); I2C_WriteByte(0x7D, 0x3A);
    read_val = I2C_ReadByte(0x7E); read_val &= ~(0x40 | 0x08); I2C_WriteByte(0x7E, read_val);
    I2C_WriteByte(0x7D, 0x3B);
    read_val = I2C_ReadByte(0x7E); read_val &= ~(0x10 | 0x02); I2C_WriteByte(0x7E, read_val);

    // 3. ODR設定 (25Hz)
    I2C_WriteByte(0x1B, 0x4B); 
    I2C_WriteByte(0x1C, 0x4B); 

    // 4. AULPモード 
    I2C_WriteByte(0x7C, 0x00); I2C_WriteByte(0x7D, 0x58);
    read_val = I2C_ReadByte(0x7E); read_val &= ~(0x10); I2C_WriteByte(0x7E, read_val);

    // 5. 平均化フィルタ 1x 
    I2C_WriteByte(0x7C, 0x00); I2C_WriteByte(0x7D, 0x81);
    read_val = I2C_ReadByte(0x7E); read_val &= 0xF0; I2C_WriteByte(0x7E, read_val);
    I2C_WriteByte(0x7C, 0x00); I2C_WriteByte(0x7D, 0xAA);
    read_val = I2C_ReadByte(0x7E); read_val &= 0xE1; I2C_WriteByte(0x7E, read_val);

    // 6. FIFO構成
    I2C_WriteByte(0x1D, 0x40); 
    I2C_WriteByte(0x21, 0x07);

    // 7. 電源有効化
    I2C_WriteByte(0x10, 0x0A);
}

// =========================================================================
// ICM45605 読み取り ＆ フィルタ更新処理 (Arduino版)
// =========================================================================
bool ICM45605_Read_Process(int32_t *ax_mg, int32_t *ay_mg, int32_t *az_mg, int16_t *gx_raw, int16_t *gy_raw, int16_t *gz_raw) {
    uint8_t count_buf[2];
    uint16_t fifo_count = 0;

    I2C_ReadBytes(0x12, count_buf, 2);
    fifo_count = (uint16_t)((count_buf[1] << 8) | count_buf[0]);

    if (fifo_count >= 16) {
        uint8_t d[16];
        I2C_ReadBytes(0x14, d, 16);

        int16_t raw_ax = (int16_t)((d[2] << 8) | d[1]);
        int16_t raw_ay = (int16_t)((d[4] << 8) | d[3]);
        int16_t raw_az = (int16_t)((d[6] << 8) | d[5]);
        int16_t raw_gx = (int16_t)((d[8] << 8)  | d[7]);
        int16_t raw_gy = (int16_t)((d[10] << 8) | d[9]);
        int16_t raw_gz = (int16_t)((d[12] << 8) | d[11]);

        *ax_mg = (int32_t)raw_ax * 1000 / 16384;
        *ay_mg = (int32_t)raw_ay * 1000 / 16384;
        *az_mg = (int32_t)raw_az * 1000 / 16384;
        *gx_raw = raw_gx; *gy_raw = raw_gy; *gz_raw = raw_gz;

        float gx_rad = ((float)raw_gx / GYRO_SENSITIVITY) * DEG_TO_RAD;
        float gy_rad = ((float)raw_gy / GYRO_SENSITIVITY) * DEG_TO_RAD;
        float gz_rad = ((float)raw_gz / GYRO_SENSITIVITY) * DEG_TO_RAD;
        float ax_f = (float)raw_ax; float ay_f = (float)raw_ay; float az_f = (float)raw_az;

        MadgwickAHRSupdateIMU(gx_rad, gy_rad, gz_rad, ax_f, ay_f, az_f, FIFO_DT);
        return true;
    }
    return false;
}

// =========================================================================
// Madgwick フィルタ 計算関数
// =========================================================================
float invSqrt(float x) {
    float halfx = 0.5f * x;
    float y = x;
    long i = *(long*)&y;
    i = 0x5f3759df - (i >> 1);
    y = *(float*)&i;
    y = y * (1.5f - (halfx * y * y));
    return y;
}

void MadgwickAHRSupdateIMU(float gx, float gy, float gz, float ax, float ay, float az, float dt) {
    float recipNorm; float s0, s1, s2, s3; float qDot1, qDot2, qDot3, qDot4;
    float _2q0, _2q1, _2q2, _2q3, _4q0, _4q1, _4q2 ,_8q1, _8q2, q0q0, q1q1, q2q2, q3q3;
    float q0 = q.w; float q1 = q.x; float q2 = q.y; float q3 = q.z;

    qDot1 = 0.5f * (-q1 * gx - q2 * gy - q3 * gz);
    qDot2 = 0.5f * ( q0 * gx + q2 * gz - q3 * gy);
    qDot3 = 0.5f * ( q0 * gy - q1 * gz + q3 * gx);
    qDot4 = 0.5f * ( q0 * gz + q1 * gy - q2 * gx);

    if(!((ax == 0.0f) && (ay == 0.0f) && (az == 0.0f))) {
        recipNorm = invSqrt(ax * ax + ay * ay + az * az);
        ax *= recipNorm; ay *= recipNorm; az *= recipNorm;
        _2q0 = 2.0f * q0; _2q1 = 2.0f * q1; _2q2 = 2.0f * q2; _2q3 = 2.0f * q3;
        _4q0 = 4.0f * q0; _4q1 = 4.0f * q1; _4q2 = 4.0f * q2; _8q1 = 8.0f * q1; _8q2 = 8.0f * q2;
        q0q0 = q0 * q0; q1q1 = q1 * q1; q2q2 = q2 * q2; q3q3 = q3 * q3;
        s0 = _4q0 * q2q2 + _2q2 * ax + _4q0 * q1q1 - _2q1 * ay;
        s1 = _4q1 * q3q3 - _2q3 * ax + 4.0f * q0q0 * q1 - _2q0 * ay - _4q1 + _8q1 * q1q1 + _8q1 * q2q2 + _4q1 * az;
        s2 = 4.0f * q0q0 * q2 + _2q0 * ax + _4q2 * q3q3 - _2q3 * ay - _4q2 + _8q2 * q1q1 + _8q2 * q2q2 + _4q2 * az;
        s3 = 4.0f * q1q1 * q3 - _2q1 * ax + 4.0f * q2q2 * q3 - _2q2 * ay;
        recipNorm = invSqrt(s0 * s0 + s1 * s1 + s2 * s2 + s3 * s3);
        s0 *= recipNorm; s1 *= recipNorm; s2 *= recipNorm; s3 *= recipNorm;
        qDot1 -= BETA * s0; qDot2 -= BETA * s1; qDot3 -= BETA * s2; qDot4 -= BETA * s3;
    }
    q0 += qDot1 * dt; q1 += qDot2 * dt; q2 += qDot3 * dt; q3 += qDot4 * dt;
    recipNorm = invSqrt(q0 * q0 + q1 * q1 + q2 * q2 + q3 * q3);
    q.w = q0 * recipNorm; q.x = q1 * recipNorm; q.y = q2 * recipNorm; q.z = q3 * recipNorm;
}