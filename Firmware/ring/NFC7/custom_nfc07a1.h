/**
  ******************************************************************************
  * @file    custom_nfc07a1.h
  * @author  MMY Application Team
  * @version 1.0.1
  * @date    27-Apr-2023
  * @brief   This file contains definitions for the bsp_nfc07a1.c
  *          board specific functions.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2021 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __CUSTOM_NFC07A1_H__
#define __CUSTOM_NFC07A1_H__

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/

#include "st25dvxxkc_conf.h"

#include "st25dvxxkc.h"

/** @addtogroup CUSTOM
  * @{
  */

/* Exported types ------------------------------------------------------------*/

/**
 * @brief  NFC07A1 Ack Nack enumerator definition
 */
typedef enum
{
  I2CANSW_ACK = 0,
  I2CANSW_NACK
}CUSTOM_I2CANSW_E;

/* External variables --------------------------------------------------------*/
/* Exported macro ------------------------------------------------------------*/
/* Exported functions ------------------------------------------------------- */
/** @defgroup ST25DVXXKC_NUCLEO_Exported_Functions
  * @{
  */
int32_t CUSTOM_GPO_Init( void );
int32_t CUSTOM_GPO_DeInit( void );
int32_t CUSTOM_GPO_ReadPin( void );
void CUSTOM_NFC07A1_GPO_IRQHandler(void);

#ifdef __cplusplus
}
#endif

#endif /* __CUSTOM_NFC07A1_H__ */

