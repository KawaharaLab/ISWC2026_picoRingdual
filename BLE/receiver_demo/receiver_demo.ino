#include <ArduinoBLE.h>
#include <string.h> // For memcpy

const char* targetServiceUuid = "19B10000-E8F2-537E-4F6C-D104768A1214";
const char* targetCharUuid    = "19B10001-E8F2-537E-4F6C-D104768A1214";

// Function prototypes
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

  // Main loop while connected
  while (peripheral.connected()) {
    if (imuCharacteristic.valueUpdated()) {
      
      // Prepare a 9-byte buffer for reception
      uint8_t byteBuffer[9];
      
      // Call the parsing function if exactly 9 bytes are received
      if (imuCharacteristic.readValue(byteBuffer, 9) == 9) {
        ParseAndPrintImuData(byteBuffer);
      }
    }
  }
}

// =========================================================================
// Packet Parsing & Serial Output Function for Unity
// =========================================================================
void ParseAndPrintImuData(uint8_t* buffer) {
  int16_t w_raw, x_raw, y_raw, z_raw;
  uint8_t gpio_byte;
  int idx = 0;

  // 1. Extract binary data (9 bytes in total)
  memcpy(&w_raw, &buffer[idx], 2); idx += 2;
  memcpy(&x_raw, &buffer[idx], 2); idx += 2;
  memcpy(&y_raw, &buffer[idx], 2); idx += 2;
  memcpy(&z_raw, &buffer[idx], 2); idx += 2;

  // GPIO Byte (1 byte)
  gpio_byte = buffer[idx];

  // 2. Decompress data (Divide by 30000.0f to restore to float)
  float w = (float)w_raw / 30000.0f;
  float x = (float)x_raw / 30000.0f;
  float y = (float)y_raw / 30000.0f;
  float z = (float)z_raw / 30000.0f;

  /* 3. Serial output for Unity */
  Serial.print("IMU:");
  Serial.print(w, 4); Serial.print(",");
  Serial.print(x, 4); Serial.print(",");
  Serial.print(y, 4); Serial.print(",");
  Serial.print(z, 4); Serial.print(",");
  Serial.println(gpio_byte); 
}