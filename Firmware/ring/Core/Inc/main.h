/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  * This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32u3xx_hal.h"

#include "st25dvxxkc_conf.h"
/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define BTN_Pin GPIO_PIN_0
#define BTN_GPIO_Port GPIOA
#define DWN_Pin GPIO_PIN_1
#define DWN_GPIO_Port GPIOA
#define UP_Pin GPIO_PIN_2
#define UP_GPIO_Port GPIOA
#define RHT_Pin GPIO_PIN_3
#define RHT_GPIO_Port GPIOA
#define LFT_Pin GPIO_PIN_4
#define LFT_GPIO_Port GPIOA
#define INT1_Pin GPIO_PIN_5
#define INT1_GPIO_Port GPIOA
#define GPO_Pin GPIO_PIN_0
#define GPO_GPIO_Port GPIOB
#define GPO_EXTI_IRQn EXTI0_IRQn
#define LPD_Pin GPIO_PIN_1
#define LPD_GPIO_Port GPIOB
#define INT2_Pin GPIO_PIN_8
#define INT2_GPIO_Port GPIOA

/* USER CODE BEGIN Private defines */

// ▼ Please uncomment the state you want to measure (Enable only one of them)
#define MODE_NORMAL              // Normal operation
//#define MODE_MEASURE_IMU_SLEEP   // IMU Sleep only (NFC performs dummy communication)
//#define MODE_MEASURE_ALL_SLEEP     // Both IMU and NFC Sleep (Ultimate standby state)

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */