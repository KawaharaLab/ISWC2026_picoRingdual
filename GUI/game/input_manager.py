import threading
import serial
import pygame
import time

class HandData:
    def __init__(self):
        self._reset_quaternion()
        self.tb_rotation_x = 0.0
        self.tb_rotation_y = 0.0
        
        # スレッド間の取りこぼしを防ぐための蓄積変数
        self._tb_acc_x = 0.0
        self._tb_acc_y = 0.0
        self._pending_click = False
        
        self.is_clicked = False
        self.is_clicking = False

    def _reset_quaternion(self):
        # デフォルトの姿勢 [x,y,z,w]
        self.quaternion = [0.0, 0.0, 0.0, 1.0]

class InputManager:
    # 1. 左右それぞれのポートを受け取れるように変更
    def __init__(self, port_right=None, port_left=None, baudrate=115200):
        self.left_hand = HandData()
        self.right_hand = HandData()
        self.active_hand = 'RIGHT'
        
        self.port_right = port_right
        self.port_left = port_left
        self.baudrate = baudrate
        
        self.thread_right = None
        self.thread_left = None
        self.running = False
        self.is_gesture_m_pressed = False

        if self.port_right or self.port_left:
            self.start_serial()

    # 2. スレッドの並列起動
    def start_serial(self):
        self.running = True
        
        if self.port_right:
            self.thread_right = threading.Thread(target=self._serial_loop, args=(self.port_right, 'RIGHT'), daemon=True)
            self.thread_right.start()
            print(f"[RIGHT] Serial started on {self.port_right}")
            
        if self.port_left:
            self.thread_left = threading.Thread(target=self._serial_loop, args=(self.port_left, 'LEFT'), daemon=True)
            self.thread_left.start()
            print(f"[LEFT] Serial started on {self.port_left}")

    def stop_serial(self):
        self.running = False
        if self.thread_right:
            self.thread_right.join()
        if self.thread_left:
            self.thread_left.join()

    # 3. 引数に「開くポート」と「手」を追加して汎用化
    def _serial_loop(self, port, hand_id):
        try:
            with serial.Serial(port, self.baudrate, timeout=0.1) as ser:
                while self.running:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self._parse_serial_line(line, hand_id)
        except Exception as e:
            print(f"Serial Error ({hand_id} on {port}): {e}")

    # 4. 「どちらの手か」を判定して振り分ける
    def _parse_serial_line(self, line, hand_id):
        try:
            if not line.startswith("IMU:"):
                return
            
            parts = line.split(":")
            if len(parts) != 2: return
            
            data = parts[1].split(",")
            if len(data) != 5: return
            
            w = float(data[0])
            x = float(data[1])
            y = float(data[2])
            z = float(data[3])
            gpio = int(data[4])
            
            converted_quat = [-x, -z, -y, w]
            
            # 対象の手のデータを特定
            hand = self.right_hand if hand_id == 'RIGHT' else self.left_hand
            
            # 【変更点】姿勢(IMU)データは常に更新するが、active_handはここでは勝手に変えない
            hand.quaternion = converted_quat
            
            # --- ボタン (押し込み) の処理 ---
            is_btn_pressed = bool(gpio & 0x10)
            
            if is_btn_pressed:
                if not hand.is_clicking: # 押し始めの瞬間
                    hand.is_clicking = True
                    
                    # 【重要】アクティブハンドの切り替えロジック
                    if self.active_hand != hand_id:
                        # 違う手がクリックされたら：切り替えだけ行う（クリックは予約しない）
                        print(f"Hand switched: {self.active_hand} -> {hand_id}")
                        self.active_hand = hand_id
                        
                        # 切り替え時のノイズ防止のため、新しい手と古い手のバッファを掃除
                        hand._tb_acc_x = 0.0
                        hand._tb_acc_y = 0.0
                    else:
                        # 同じ手がクリックされたら：通常通りクリックをアプリに伝える
                        hand._pending_click = True
                        
                        # 【直前キャンセル】
                        hand._tb_acc_x = 0.0
                        hand._tb_acc_y = 0.0
            else:
                if hand.is_clicking: # 離した瞬間
                    hand.is_clicking = False

            # --- スクロール処理 ---
            # 基本的にアクティブな手のみスクロールを蓄積する（好みで変更可能）
            if self.active_hand == hand_id:
                move_speed = 25.0  
                if gpio & 0x01: hand._tb_acc_x -= move_speed
                if gpio & 0x02: hand._tb_acc_x += move_speed
                if gpio & 0x04: hand._tb_acc_y -= move_speed
                if gpio & 0x08: hand._tb_acc_y += move_speed
                
        except (ValueError, IndexError):
            pass

    def __del__(self):
        self.stop_serial()

    def process_pygame_events(self, events):
        self.left_hand.is_clicked = False
        self.right_hand.is_clicked = False

        # スクロールの不感帯と主軸ロック
        DEADZONE = 40.0 
        for hand in (self.left_hand, self.right_hand):
            if hand._pending_click:
                hand.is_clicked = True
                hand._pending_click = False

            abs_x = abs(hand._tb_acc_x)
            abs_y = abs(hand._tb_acc_y)

            if abs_x > DEADZONE or abs_y > DEADZONE:
                if abs_x >= abs_y:
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

        # --- キーボードデバッグ（完全復元版） ---
        keys = pygame.key.get_pressed()
        kb_move_speed = 10.0
        
        # [右手] 矢印キー（※スクロール操作ではactive_handは切り替えない）
        if keys[pygame.K_LEFT]: 
            self.right_hand.tb_rotation_x -= kb_move_speed
        if keys[pygame.K_RIGHT]: 
            self.right_hand.tb_rotation_x += kb_move_speed
        if keys[pygame.K_UP]: 
            self.right_hand.tb_rotation_y -= kb_move_speed
        if keys[pygame.K_DOWN]: 
            self.right_hand.tb_rotation_y += kb_move_speed

        # [左手] WASDキー
        if keys[pygame.K_a]: 
            self.left_hand.tb_rotation_x -= kb_move_speed
        if keys[pygame.K_d]: 
            self.left_hand.tb_rotation_x += kb_move_speed
        if keys[pygame.K_w]: 
            self.left_hand.tb_rotation_y -= kb_move_speed
        if keys[pygame.K_s]: 
            self.left_hand.tb_rotation_y += kb_move_speed

        # 姿勢リセット用のMキー
        self.is_gesture_m_pressed = keys[pygame.K_m]

        for event in events:
            if event.type == pygame.KEYDOWN:
                # 右手操作 (SPACE)
                if event.key == pygame.K_SPACE:
                    if self.active_hand != 'RIGHT':
                        self.active_hand = 'RIGHT'
                        print("Switched to RIGHT (Keyboard)")
                    else:
                        self.right_hand.is_clicked = True
                        self.right_hand.is_clicking = True
                
                # 左手操作 (LSHIFT)
                if event.key == pygame.K_LSHIFT:
                    if self.active_hand != 'LEFT':
                        self.active_hand = 'LEFT'
                        print("Switched to LEFT (Keyboard)")
                    else:
                        self.left_hand.is_clicked = True
                        self.left_hand.is_clicking = True
            
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    self.right_hand.is_clicking = False
                if event.key == pygame.K_LSHIFT:
                    self.left_hand.is_clicking = False

    def get_active_hand_data(self):
        hand = self.right_hand if self.active_hand == 'RIGHT' else self.left_hand
        if self.is_gesture_m_pressed:
            hand.quaternion = [0.7071, 0.0, 0.0, 0.7071]
        return hand

    def get_active_hand_id(self):
        return self.active_hand