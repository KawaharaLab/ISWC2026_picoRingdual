/* nfc_app.h */
#ifndef NFC_APP_H
#define NFC_APP_H

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"

/* User public functions */
void NFC_User_Init(void);
void NFC_User_Process(uint8_t* left, uint8_t* right, uint8_t* up, uint8_t* down, uint8_t* btn);

#ifdef __cplusplus
}
#endif

#endif /* NFC_APP_H */