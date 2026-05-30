import threading
import serial
import pygame
import time
import glm
import math

class HandData:
    def __init__(self):
        self.quaternion = [0.0, 0.0, 0.0, 1.0]
        self.tb_rotation_x = 0.0
        self.tb_rotation_y = 0.0
        self._tb_acc_x = 0.0
        self._tb_acc_y = 0.0
        self._pending_click = False
        self.is_clicked = False
        self.is_clicking = False
        # 滑らかにするための保持変数
        self.filtered_yaw = 0.0
        self.filtered_pitch = 0.0
        # 基準点（オフセット）
        self.offset_yaw = 0.0
        self.offset_pitch = 0.0

    def get_euler(self):
        # クォータニオンの成分 (x, y, z, w の順序はデバイスの仕様に合わせる)
        x, y, z, w = self.quaternion

        # --- 画面上の「上下(Pitch)」：コントローラーのX軸周りの回転を取り出す ---
        # 以前はここがズレていたため反応しなかった、あるいは別の動きになっていました
        sinp = 2 * (w * x - y * z)
        raw_pitch = math.asin(max(-1.0, min(1.0, sinp)))
        
        # --- 画面上の「左右(Yaw)」：コントローラーのY軸周りの回転を取り出す ---
        siny_cosp = 2 * (w * y + z * x)
        cosy_cosp = 1 - 2 * (x * x + y * y)
        raw_yaw = math.atan2(siny_cosp, cosy_cosp)

        # 1.0 は感度調整用
        target_yaw = (raw_yaw - self.offset_yaw) * 1.0
        target_pitch = (raw_pitch - self.offset_pitch) * -1.0

        # 平滑化フィルタ
        smooth_factor = 0.15 
        self.filtered_yaw += (target_yaw - self.filtered_yaw) * smooth_factor
        self.filtered_pitch += (target_pitch - self.filtered_pitch) * smooth_factor

        return self.filtered_yaw, self.filtered_pitch

    def reset_view(self):
        """現在のIMUの値を『正面（0,0）』として登録する"""
        x, z, y, w = self.quaternion
        sinp = 2 * (w * y - z * x)
        self.offset_pitch = math.asin(max(-1.0, min(1.0, sinp)))
        
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        self.offset_yaw = math.atan2(siny_cosp, cosy_cosp)
        
        # フィルタ値も即座にリセットして、パッと正面を向くようにする
        self.filtered_yaw = 0.0
        self.filtered_pitch = 0.0

class InputManager:
    def __init__(self, port_right='/dev/cu.usbmodem1101', port_left=None, baudrate=115200):
        self.left_hand = HandData()
        self.right_hand = HandData()
        self.active_hand = 'RIGHT'
        self.port_right = port_right
        self.port_left = port_left
        self.baudrate = baudrate
        self.running = False
        if self.port_right or self.port_left:
            self.start_serial()

    def start_serial(self):
        self.running = True
        if self.port_right:
            threading.Thread(target=self._serial_loop, args=(self.port_right, 'RIGHT'), daemon=True).start()
        if self.port_left:
            threading.Thread(target=self._serial_loop, args=(self.port_left, 'LEFT'), daemon=True).start()

    def _serial_loop(self, port, hand_id):
        try:
            with serial.Serial(port, self.baudrate, timeout=0.1) as ser:
                while self.running:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line.startswith("IMU:"):
                        self._parse_serial_line(line, hand_id)
        except Exception as e:
            print(f"Serial Error: {e}")

    def _parse_serial_line(self, line, hand_id):
        try:
            data = line.split(":")[1].split(",")
            w, x, y, z = map(float, data[:4])
            gpio = int(data[4])
            hand = self.right_hand if hand_id == 'RIGHT' else self.left_hand
            hand.quaternion = [-x, -z, -y, w]
            
            # 射撃 (押し込み)
            if bool(gpio & 0x10):
                if not hand.is_clicking:
                    hand.is_clicking = True
                    hand._pending_click = True
            else:
                hand.is_clicking = False

            # スクロール (リロード/ズーム)
            move_speed = 30.0  
            if gpio & 0x01: hand._tb_acc_x -= move_speed # 左
            if gpio & 0x02: hand._tb_acc_x += move_speed # 右
            if gpio & 0x04: hand._tb_acc_y -= move_speed # 上
            if gpio & 0x08: hand._tb_acc_y += move_speed # 下
        except: pass

    def update(self):
        """毎フレーム呼び出して蓄積された入力を処理"""
        DEADZONE = 40.0 
        for hand in (self.left_hand, self.right_hand):
            hand.is_clicked = hand._pending_click
            hand._pending_click = False
            
            if abs(hand._tb_acc_x) > DEADZONE or abs(hand._tb_acc_y) > DEADZONE:
                if abs(hand._tb_acc_x) >= abs(hand._tb_acc_y):
                    hand.tb_rotation_x = hand._tb_acc_x
                    hand.tb_rotation_y = 0.0
                else:
                    hand.tb_rotation_x = 0.0
                    hand.tb_rotation_y = hand._tb_acc_y
                hand._tb_acc_x = 0.0
                hand._tb_acc_y = 0.0
            else:
                hand.tb_rotation_x = 0.0
                hand.tb_rotation_y = 0.0

    def get_active_hand_data(self):
        return self.right_hand if self.active_hand == 'RIGHT' else self.left_hand