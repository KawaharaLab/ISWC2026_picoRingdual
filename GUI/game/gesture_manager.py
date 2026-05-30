import numpy as np
from scipy.spatial.transform import Rotation as R

class GestureManager:
    def __init__(self, input_manager):
        self.input_manager = input_manager
        self.on_menu_triggered = None
        self.is_menu_gesture_active = False

    def update(self):
        hand_data = self.input_manager.get_active_hand_data()
        active_hand_id = self.input_manager.get_active_hand_id() # 'RIGHT' or 'LEFT'を取得
        
        try:
            rot = R.from_quat(hand_data.quaternion)
            # Z-axis forward vector
            forward_vector = rot.apply([0, 0, 1])
            y_val = forward_vector[1]
            
            # --- 手に応じて判定条件を分ける ---
            if active_hand_id == 'RIGHT':
                # 右手：通常通り、センサーが下（-0.8以下）を向いたらトリガー
                trigger_condition = y_val <= -0.8
                reset_condition = y_val > -0.2
            else:
                # 左手：180度逆なので、センサーが上（0.8以上）を向いたら物理的な「下」とみなす
                trigger_condition = y_val >= 0.8
                reset_condition = y_val < 0.2
            
            # --- ジェスチャーの判定 ---
            if trigger_condition:
                if not self.is_menu_gesture_active:
                    print(f"DEBUG: Gesture Triggered ({active_hand_id})! Y={y_val:.2f}")
                    self.is_menu_gesture_active = True
                    if self.on_menu_triggered:
                        self.on_menu_triggered()
            elif reset_condition: # Reset when pointing roughly forward/up (or down for left hand)
                if self.is_menu_gesture_active:
                    # print(f"DEBUG: Gesture Reset ({active_hand_id})")
                    self.is_menu_gesture_active = False
                
        except ValueError:
            # Handle invalid quaternions (e.g. all zeros) gracefully
            pass