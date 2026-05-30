#include <ArduinoBLE.h>
#include <string.h> // memcpy用

const char* targetServiceUuid = "19B10000-E8F2-537E-4F6C-D104768A1214";
const char* targetCharUuid    = "19B10001-E8F2-537E-4F6C-D104768A1214";

// プロトタイプ宣言
void ParseAndPrintImuData(uint8_t* buffer);
void explorePeripheral(BLEDevice peripheral);

void setup() {
  Serial.begin(9600);
  while (!Serial); 

  if (!BLE.begin()) {
    Serial.println("Starting BLE Central failed!");
    while (1);
  }

  Serial.println("XIAO(B) Central - Unity Packet Receiver Started.");
  BLE.scanForUuid(targetServiceUuid);
}

void loop() {
  BLEDevice peripheral = BLE.available();

  if (peripheral) {
    if (peripheral.localName() == "XIAO_IMU_A") {
      BLE.stopScan();
      explorePeripheral(peripheral);
      BLE.scanForUuid(targetServiceUuid);
    }
  }
}

void explorePeripheral(BLEDevice peripheral) {
  if (!peripheral.connect()) return;
  if (!peripheral.discoverAttributes()) {
    peripheral.disconnect();
    return;
  }

  BLECharacteristic imuCharacteristic = peripheral.characteristic(targetCharUuid);
  if (!imuCharacteristic) {
    peripheral.disconnect();
    return;
  }

  if (imuCharacteristic.canSubscribe()) {
    imuCharacteristic.subscribe();
  } else {
    peripheral.disconnect();
    return;
  }

  // つながっている間のメインループ
  while (peripheral.connected()) {
    if (imuCharacteristic.valueUpdated()) {
      
      // 【変更】9バイトの受信用バッファを用意
      uint8_t byteBuffer[9];
      
      // 9バイトきっちり届いたら、提示された解析関数を叩く
      if (imuCharacteristic.readValue(byteBuffer, 9) == 9) {
        ParseAndPrintImuData(byteBuffer);
      }
    }
  }
}

// =========================================================================
// 提示されたパケット解析＆Unity用シリアル出力関数
// =========================================================================
void ParseAndPrintImuData(uint8_t* buffer) {
  int16_t w_raw, x_raw, y_raw, z_raw;
  uint8_t gpio_byte;
  int idx = 0;

  // 1. バイナリデータの取り出し (合計9バイト)
  memcpy(&w_raw, &buffer[idx], 2); idx += 2;
  memcpy(&x_raw, &buffer[idx], 2); idx += 2;
  memcpy(&y_raw, &buffer[idx], 2); idx += 2;
  memcpy(&z_raw, &buffer[idx], 2); idx += 2;

  // GPIO Byte (1 byte)
  gpio_byte = buffer[idx];

  // 2. 圧縮データの復元 (30000.0f で割って float に戻す)
  float w = (float)w_raw / 30000.0f;
  float x = (float)x_raw / 30000.0f;
  float y = (float)y_raw / 30000.0f;
  float z = (float)z_raw / 30000.0f;

  /* 3. Unity用シリアル出力 */
  Serial.print("IMU:");
  Serial.print(w, 4); Serial.print(",");
  Serial.print(x, 4); Serial.print(",");
  Serial.print(y, 4); Serial.print(",");
  Serial.print(z, 4); Serial.print(",");
  Serial.println(gpio_byte); 
}