/* nfc_app.c */
#include "nfc_app.h"
#include "custom_nfc07a1_nfctag.h"
#include <stdio.h>
#include <string.h>
#include "ICM45605.h" // Changed from BMI270 to ICM45605
#include "main.h" 

/* Reference to external variables (UART handle from main.c) */
extern UART_HandleTypeDef huart1;

/* Constant Definitions */
#define IMU_DATA_SIZE 32
#define NFC_INSTANCE  0 
#define GPIO_THRESHOLD 2    

/* Global Variables */
static uint8_t demo_counter = 0;
static uint8_t awritedata[IMU_DATA_SIZE];

static ST25DVxxKC_MB_CTRL_DYN_STATUS_t mbctrldynstatus;
static ST25DVxxKC_EN_STATUS_E MB_mode;
static ST25DVxxKC_PASSWD_t passwd;
static ST25DVxxKC_I2CSSO_STATUS_E i2csso;

void UART_PrintHex(UART_HandleTypeDef *huart, uint32_t val) {
    char hex_chars[] = "0123456789ABCDEF";
    uint8_t buf[11]; 
    
    buf[0] = '0';
    buf[1] = 'x';
    for (int i = 7; i >= 0; i--) {
        buf[i + 2] = hex_chars[val & 0xF];
        val >>= 4;
    }
    buf[10] = '\0';
    
    HAL_UART_Transmit(huart, buf, 10, 100);
}

void NFC_User_Init(void)
{
  int32_t ret;
  uint8_t mblength = 0;
  char buffer[64]; 
  
  HAL_UART_Transmit(&huart1, (uint8_t*)"\r\n--- NFC Init Start ---\r\n", 26, 100);

  do {
      ret = CUSTOM_NFCTAG_Init(NFC_INSTANCE);
      if (ret != NFCTAG_OK) {
        HAL_UART_Transmit(&huart1, (uint8_t*)"Error: ", 7, 100);
        UART_PrintHex(&huart1, (uint32_t)ret); 
        HAL_UART_Transmit(&huart1, (uint8_t*)"\r\n", 2, 100);
        HAL_Delay(500); 
    }
  } while (ret != NFCTAG_OK);

  HAL_UART_Transmit(&huart1, (uint8_t*)"NFC Init Done.\r\n", 16, 100);

  CUSTOM_NFCTAG_ReadMBMode(NFC_INSTANCE, &MB_mode);
  
  if(MB_mode == ST25DVXXKC_DISABLE)
  {
    HAL_UART_Transmit(&huart1, (uint8_t*)"MB is disabled. Enabling...\r\n", 29, 100);
    CUSTOM_NFCTAG_ReadI2CSecuritySession_Dyn(NFC_INSTANCE, &i2csso);
    
    if(i2csso == ST25DVXXKC_SESSION_CLOSED)
    {
      passwd.MsbPasswd = 0; 
      passwd.LsbPasswd = 0; 
      CUSTOM_NFCTAG_PresentI2CPassword(NFC_INSTANCE, passwd);
    }
    
    CUSTOM_NFCTAG_WriteMBMode(NFC_INSTANCE, ST25DVXXKC_ENABLE);
  }

  CUSTOM_NFCTAG_SetMBEN_Dyn(NFC_INSTANCE);
  HAL_UART_Transmit(&huart1, (uint8_t*)"Mailbox Activated.\r\n", 20, 100);

  CUSTOM_NFCTAG_ReadMBLength_Dyn(NFC_INSTANCE, &mblength);
  sprintf(buffer, "MB Length: %d bytes\r\n", mblength + 1);
  HAL_UART_Transmit(&huart1, (uint8_t*)buffer, strlen(buffer), 100);
  HAL_UART_Transmit(&huart1, (uint8_t*)"--- NFC Init Complete ---\r\n", 27, 100);
}

void NFC_User_Process(uint8_t* left, uint8_t* right, uint8_t* up, uint8_t* down, uint8_t* btn)
{
  // 1. Read sensor data (The Madgwick filter runs internally and updates the global variable 'q')
  int32_t ax_mg = 0, ay_mg = 0, az_mg = 0;
  int16_t gx = 0, gy = 0, gz = 0;
  
#ifdef MEASURE_SLEEP_MODE
  // [Sleep Measurement Mode]
  // Do nothing or insert dummy orientation data
#else
  // [Normal Operation Mode]
  // q.w, q.x, q.y, and q.z are updated to the latest values inside ICM45605_Read_Process
  ICM45605_Read_Process(&ax_mg, &ay_mg, &az_mg, &gx, &gy, &gz);
#endif

  // Enable Mailbox
  CUSTOM_NFCTAG_SetMBEN_Dyn(NFC_INSTANCE);

  /* 2. Check Mailbox Status */
  CUSTOM_NFCTAG_ReadMBCtrl_Dyn(NFC_INSTANCE, &mbctrldynstatus);

  if(mbctrldynstatus.HostPutMsg == 0) 
  {
    /* --- A. GPIO Evaluation Logic --- */
    uint8_t u_act = 0;
    uint8_t d_act = 0;
    uint8_t r_act = 0;
    uint8_t l_act = 0;

    // Follow the current simple input logic
    if (*up > 0)    u_act = 1;
    if (*down > 0)  l_act = 1;
    if (*right > 0) r_act = 1;
    if (*left > 0)  d_act = 1;

    // --- Bit Packing ---
    uint8_t gpio_byte = 0;
    if (l_act) gpio_byte |= 0x01; // Bit 0: Left
    if (r_act) gpio_byte |= 0x02; // Bit 1: Right
    if (u_act) gpio_byte |= 0x04; // Bit 2: Up
    if (d_act) gpio_byte |= 0x08; // Bit 3: Down
    if (*btn)  gpio_byte |= 0x10; // Bit 4: Btn

    /* --- B. IMU Data (Quaternion) Compression --- */
    // Scale values ranging from -1.0f to 1.0f by 30000.0f and cast to int16_t
    int16_t w_val = (int16_t)(q.w * 30000.0f);
    int16_t x_val = (int16_t)(q.x * 30000.0f);
    int16_t y_val = (int16_t)(q.y * 30000.0f);
    int16_t z_val = (int16_t)(q.z * 30000.0f);

    /* --- C. Data Packing (9 Bytes) --- */
    awritedata[0] = (uint8_t)(w_val & 0xFF);
    awritedata[1] = (uint8_t)((w_val >> 8) & 0xFF);
    awritedata[2] = (uint8_t)(x_val & 0xFF);
    awritedata[3] = (uint8_t)((x_val >> 8) & 0xFF);
    awritedata[4] = (uint8_t)(y_val & 0xFF);
    awritedata[5] = (uint8_t)((y_val >> 8) & 0xFF);
    awritedata[6] = (uint8_t)(z_val & 0xFF);
    awritedata[7] = (uint8_t)((z_val >> 8) & 0xFF);

    awritedata[8] = gpio_byte;

    /* --- D. Execute Write Operation --- */
    uint16_t txLen = 9; 
    CUSTOM_NFCTAG_WriteMailboxData(NFC_INSTANCE, awritedata, txLen);
  }
}