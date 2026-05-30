/**
 ******************************************************************************
 * @file    st25dvxxkc_conf.h
 * @author  SRA Application Team
 * @version V1.0.1
 * @date    27-Apr-2023
 * @brief   This file contains definitions for the ST25DVXXKC bus interfaces
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
#ifndef __ST25DVXXKC_CONF_H__
#define __ST25DVXXKC_CONF_H__

#ifdef __cplusplus
extern "C" {
#endif

#include "stm32u3xx_hal.h"
#include "custom_bus.h"
#include "custom_errno.h"
#include "stm32u3xx_hal_exti.h"

#define CUSTOM_ST25DVXXKC_I2C_Init         BSP_I2C3_Init
#define CUSTOM_ST25DVXXKC_I2C_DeInit       BSP_I2C3_DeInit
#define CUSTOM_ST25DVXXKC_I2C_ReadReg16    BSP_I2C3_ReadReg16
#define CUSTOM_ST25DVXXKC_I2C_WriteReg16   BSP_I2C3_WriteReg16
#define CUSTOM_ST25DVXXKC_I2C_Recv         BSP_I2C3_Recv
#define CUSTOM_ST25DVXXKC_I2C_IsReady      BSP_I2C3_IsReady

#define CUSTOM_ST25DVXXKC_GetTick HAL_GetTick

#define ST25DVXXKC_INT_PIN_GPO_EXTI_PORT GPIOB
#define ST25DVXXKC_INT_PIN_GPO_EXTI_PIN GPIO_PIN_0
#define ST25DVXXKC_INT_PIN_GPO_EXTI_LINE EXTI_LINE_0
#define ST25DVXXKC_INT_PIN_GPO_EXTI_IRQn EXTI0_IRQn
extern EXTI_HandleTypeDef CUSTOM_NFC07A1_GPO_EXTI;
#define H_EXTI_0  CUSTOM_NFC07A1_GPO_EXTI

#define CUSTOM_NFCTAG_INSTANCE         (0)
#define CUSTOM_NFCTAG_GPO_PRIORITY     (0)
#ifdef __cplusplus
}
#endif

#endif /* __ST25DVXXKC_CONF_H__*/

