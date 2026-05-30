import sys
import serial
import numpy as np
import time
from collections import deque
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget
from PyQt6.QtCore import QTimer, Qt, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from stl import mesh
from PyQt6.QtCore import QElapsedTimer

# --- 設定 ---
PORT_LEFT = "/dev/cu.usbmodem11201"
PORT_RIGHT = "/dev/cu.usbmodem11101"
BAUD_RATE = 115200
STL_PATH = "./ring_by_yamamoto_90deg.stl"
HISTORY_LEN = 100

# グローバルなフォント設定
FONT_SIZE_TITLE = '20pt' # タイトルをさらに大きく
FONT_SIZE_AXIS = '14pt'

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
pg.setConfigOptions(antialias=True)

def load_stl(file_path):
    try:
        stl_mesh = mesh.Mesh.from_file(file_path)
        verts = stl_mesh.vectors.reshape(-1, 3)
        verts = verts * 0.375 
        faces = np.arange(len(verts)).reshape(-1, 3)
        return gl.MeshData(vertexes=verts, faces=faces)
    except Exception as e:
        print(f"STL Load Error: {e}")
        return None

class TrackballWidget(QWidget):
    def __init__(self, theme_color, label):
        super().__init__()
        self.setMinimumHeight(250)
        self.ball_pos = QPointF(0, 0)
        self.btn_pressed = False
        self.direction_states = [0, 0, 0, 0] # [L, R, U, D]
        self.theme_color = theme_color
        self.label = label

        # アニメーション管理用
        self.is_animating = False
        self.anim_timer = QElapsedTimer()
        self.current_target = QPointF(0, 0)
        self.center_pos = QPointF(0, 0)
        
        # 定数
        self.STICK_MS = 300   # 縁に吸着する時間
        self.RETURN_MS = 400  # 中心に戻る時間

    def update_state(self, gpio):
        # 1. 物理的な状態を取得
        l, r, u, d = (gpio & 1), (gpio >> 1) & 1, (gpio >> 2) & 1, (gpio >> 3) & 1
        current_press = (gpio >> 4) & 1
        was_pressed = self.btn_pressed
        self.btn_pressed = current_press
        effective_gpio = (current_press << 4)

        # プレス開始時: スクロール演出を即時キャンセルし、中央プレス演出に切り替える
        if self.btn_pressed and not was_pressed:
            self.is_animating = False
            self.direction_states = [0, 0, 0, 0]
            self.current_target = self.center_pos
            self.ball_pos = self.center_pos

        # プレス中は常に中央固定（スクロール方向演出は出さない）
        if self.btn_pressed:
            self.ball_pos = self.center_pos
            self.direction_states = [0, 0, 0, 0]
            self.update()
            return effective_gpio

        # 2. アニメーションロジック
        if self.is_animating:
            elapsed = self.anim_timer.elapsed()
            
            if elapsed < self.STICK_MS:
                # フェーズ1: 縁に吸着（入力を完全に無視してターゲット位置を維持）
                self.ball_pos = self.current_target
            elif elapsed < (self.STICK_MS + self.RETURN_MS):
                # フェーズ2: 中心へゆっくり戻る
                t = (elapsed - self.STICK_MS) / self.RETURN_MS
                # easing out: 徐々に減速
                ratio = 1.0 - (1.0 - (1.0 - t)**2)
                self.ball_pos = self.current_target * ratio
            else:
                # アニメーション終了
                self.is_animating = False
                self.direction_states = [0, 0, 0, 0]
                self.ball_pos = QPointF(0, 0)
        
        else:
            # 3. 待機中：物理的な方向入力を監視
            if l or r or u or d:
                # 入力があった瞬間、アニメーションシーケンス開始
                self.is_animating = True
                self.anim_timer.start()
                
                # 最初に見つけた方向のみをターゲットにする（斜め入力の排除）
                if u:
                    self.direction_states = [0, 0, 1, 0]
                    self.current_target = QPointF(0, -1.0)
                elif d:
                    self.direction_states = [0, 0, 0, 1]
                    self.current_target = QPointF(0, 1.0)
                elif l:
                    self.direction_states = [1, 0, 0, 0]
                    self.current_target = QPointF(-1.0, 0)
                elif r:
                    self.direction_states = [0, 1, 0, 0]
                    self.current_target = QPointF(1.0, 0)
                
                self.ball_pos = self.current_target
                # 実際に採用された方向のみをGPIOに反映
                if u:
                    effective_gpio |= (1 << 2)
                elif d:
                    effective_gpio |= (1 << 3)
                elif l:
                    effective_gpio |= (1 << 0)
                elif r:
                    effective_gpio |= (1 << 1)

        self.update()
        return effective_gpio

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        rect = self.rect()
        center = rect.center()
        
        # タイトル描画
        painter.setPen(QColor(0, 0, 0))
        painter.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        painter.drawText(rect.adjusted(0, 10, 0, 0), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self.label)

        radius = min(rect.width(), rect.height()) // 4
        painter.setPen(QPen(QColor(220, 220, 220), 3))
        painter.drawEllipse(center, radius, radius)
        
        # 方向インジケータ（direction_statesが1の間だけ点灯）
        for i, pos in enumerate([(-radius-35, -10), (radius+15, -10), (-10, -radius-35), (-10, radius+15)]):
            color = self.theme_color if self.direction_states[i] else QColor(240, 240, 240)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(center.x() + pos[0], center.y() + pos[1], 25, 25)
            
        # ボールの描画位置（self.ball_posはアニメーションシーケンスによって制御される）
        ball_x = center.x() + self.ball_pos.x() * radius
        ball_y = center.y() + self.ball_pos.y() * radius
        
        # プレスの強調アニメーション（アニメーション中でもリアルタイムに反応）
        if self.btn_pressed:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(self.theme_color, 8))
            painter.drawEllipse(QPointF(ball_x, ball_y), radius * 0.9, radius * 0.9)
            b_size = radius * 0.85 
            ball_color = self.theme_color.darker(150)
        else:
            b_size = radius * 0.7
            ball_color = self.theme_color
            painter.setPen(Qt.PenStyle.NoPen)

        painter.setBrush(QBrush(ball_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(ball_x, ball_y), b_size, b_size)

class HandModule:
    def __init__(self, name, port, color_tuple, invert_pitch=False): # invert_pitchを追加
        self.name = name
        self.port = port
        self.base_color = color_tuple 
        self.invert_pitch = invert_pitch # フラグを保存
        self.serial = None
        self.offset_q = np.array([1.0, 0.0, 0.0, 0.0])
        self.is_first_data = True
        self.prev_press = False
        self.scroll_ignore_until = 0.0
        self.scroll_ignore_after_release_s = 0.3
        self.gpio_history = [deque([0]*HISTORY_LEN, maxlen=HISTORY_LEN) for _ in range(5)]
        self.q_history = [deque([0]*HISTORY_LEN, maxlen=HISTORY_LEN) for _ in range(4)]
        
        q_color = QColor(int(color_tuple[0]*255), int(color_tuple[1]*255), int(color_tuple[2]*255))
        self.trackball = TrackballWidget(q_color, f"{self.name} Status")
        
        self.view_imu = gl.GLViewWidget()
        self.view_imu.setBackgroundColor('w')
        self.view_imu.setCameraPosition(distance=12, elevation=20, azimuth=270)
        
        self.plot_gpio = pg.PlotWidget()
        self.plot_q = pg.PlotWidget()
        self.curves_gpio = []
        self.curves_q = []
        
        self.setup_ui()
        self.connect_serial()

    def setup_ui(self):
        title_style = {'color': '#000', 'size': FONT_SIZE_TITLE, 'bold': True}
        label_font = QFont("Arial", 20)

        # --- GPIO Plot ---
        self.plot_gpio.setTitle(f"{self.name} GPIO", **title_style)
        self.plot_gpio.setYRange(-0.5, 5.5)
        
        y_axis = self.plot_gpio.getAxis('left')
        y_axis.setTicks([[(i + 0.4, n) for i, n in enumerate(["Left", "Right", "Up", "Down", "Press"])]])
        y_axis.setStyle(tickFont=label_font, tickTextOffset=20) 
        y_axis.setWidth(80) # 文字が大きくなったので幅をさらに拡大
        y_axis.setPen(pg.mkPen('k', width=2))
        
        x_axis_gpio = self.plot_gpio.getAxis('bottom')
        x_axis_gpio.setStyle(tickFont=label_font)
        x_axis_gpio.setHeight(80)
        x_axis_gpio.setTickSpacing(50, 50)

        colors_gpio = ['#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4']
        for i in range(5):
            self.curves_gpio.append(self.plot_gpio.plot(pen=pg.mkPen(colors_gpio[i], width=6)))
        
        # --- Quaternion Plot ---
        self.plot_q.setTitle(f"{self.name} Quaternion", **title_style)
        self.plot_q.setYRange(-1.1, 1.1)
        
        y_axis_q = self.plot_q.getAxis('left')
        y_axis_q.setStyle(tickFont=label_font)
        y_axis_q.setWidth(80)
        y_axis_q.setTickSpacing(1.0, 0.5) 

        x_axis_q = self.plot_q.getAxis('bottom')
        x_axis_q.setStyle(tickFont=label_font)
        x_axis_q.setHeight(80)
        x_axis_q.setTickSpacing(50, 50)
        
        q_colors = ['#000000', '#ff0000', '#00ff00', '#0000ff']
        for i in range(4):
            self.curves_q.append(self.plot_q.plot(pen=pg.mkPen(q_colors[i], width=6)))

        # --- 3D Model ---
        md = load_stl(STL_PATH)
        if md:
            self.container = gl.GLMeshItem(meshdata=md, smooth=True, drawEdges=True, edgeColor=(0,0,0,0.1))
        else:
            self.container = gl.GLMeshItem(meshdata=gl.MeshData.cylinder(rows=10, cols=30, radius=[0.5, 0.5], length=0.2), smooth=True)
        
        self.container.setColor((0.7, 0.7, 0.7, 1.0))
        self.view_imu.addItem(self.container)
        
        self.beam = gl.GLMeshItem(meshdata=gl.MeshData.cylinder(rows=4, cols=10, radius=[0.08, 0.08], length=15.0), smooth=True)
        self.beam.setColor(self.base_color)
        self.beam.rotate(-90, 1, 0, 0)
        self.beam.setParentItem(self.container)

    def connect_serial(self):
        try:
            self.serial = serial.Serial(self.port, BAUD_RATE, timeout=0.01)
        except:
            print(f"Error: Could not open {self.port}")

    def process_data(self):
        if not self.serial or not self.serial.is_open: return
        try:
            while self.serial.in_waiting:
                line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith("IMU:"):
                    vals = line.split(":")[1].split(",")
                    if len(vals) >= 5:
                        raw_q = np.array([float(vals[0]), float(vals[1]), float(vals[2]), float(vals[3])])
                        gpio_byte = int(vals[4])
                        now = time.monotonic()
                        current_press = ((gpio_byte >> 4) & 1) == 1

                        # プレス終了から0.3秒間はスクロール入力を無効化
                        if self.prev_press and not current_press:
                            self.scroll_ignore_until = now + self.scroll_ignore_after_release_s

                        ignore_scroll_input = current_press or (now < self.scroll_ignore_until)
                        filtered_gpio_byte = gpio_byte
                        if ignore_scroll_input:
                            # 無効化中は方向入力(L/R/U/D)を完全に無視し、表示にも反映しない
                            filtered_gpio_byte = gpio_byte & (1 << 4)
                        self.prev_press = current_press

                        if self.invert_pitch:
                            tempa = raw_q[3]
                            tempb = raw_q[2] # y成分を反転
                            tempc = raw_q[1]
                            tempd = raw_q[0]
                            raw_q[2] = -raw_q[2]
                            #raw_q[0] = -raw_q[0]
                            raw_q[1] = -raw_q[1]
                            #raw_q[3] = -raw_q[3]

                        # --- ここが重要：Rキーを押した後の初回データでオフセットを更新 ---
                        if self.is_first_data:
                            # 現在の raw_q の逆回転（共役）をオフセットとして保存
                            self.offset_q = np.array([raw_q[0], -raw_q[1], -raw_q[2], -raw_q[3]])
                            self.is_first_data = False
                        
                        # オフセットを適用して、現在の姿勢を「正面（0）」からの相対値にする
                        q = self.quaternion_multiply(self.offset_q, raw_q)
                        
                        # グラフ更新用
                        for i in range(4): self.q_history[i].append(raw_q[i])
                        effective_gpio = self.trackball.update_state(filtered_gpio_byte)
                        for i in range(5): self.gpio_history[i].append((effective_gpio >> i) & 1)
                        
                        self.update_animation(q, effective_gpio)
        except: pass

    def update_animation(self, q, gpio):
        w, x, y, z = q
        
        # 1. 回転角（θ）と回転軸を抽出
        # w = cos(θ/2) なので θ = 2 * acos(w)
        angle_rad = 2 * np.arccos(np.clip(w, -1.0, 1.0))
        norm = np.sqrt(x*x + y*y + z*z)
        
        if norm > 0.0001:
            # --- 増幅処理 ---
            AMPLIFICATION_FACTOR = 2  # ここを 1.5 〜 3.0 くらいで調整
            angle_deg = (angle_rad * 180 / np.pi) * AMPLIFICATION_FACTOR
            
            # 軸の方向
            ax, ay, az = x/norm, y/norm, z/norm
                
            self.container.resetTransform()
            # 増幅された角度で回転を適用
            self.container.rotate(angle_deg, ax, ay, az)
            
            # ビームの表示・非表示（変更なし）
            if (gpio >> 4) & 1:
                self.beam.setColor((self.base_color[0], self.base_color[1], self.base_color[2], 1.0))
            else:
                self.beam.setColor((self.base_color[0], self.base_color[1], self.base_color[2], 0.4))

    def update_plots(self):
        for i in range(5): self.curves_gpio[i].setData([(v * 0.8) + i for v in self.gpio_history[i]])
        for i in range(4): self.curves_q[i].setData(list(self.q_history[i]))

    def quaternion_multiply(self, q1, q2):
        w1, x1, y1, z1 = q1
        w2, x2, y2, z2 = q2
        return np.array([
            w1*w2 - x1*x2 - y1*y2 - z1*z2,
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2
        ])

class DualSensorViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dual NFC Ring Monitor")
        self.resize(1800, 1000)
        self.setStyleSheet("background-color: white;")
        
        # 左手だけ invert_pitch=True に設定
        self.left_hand = HandModule("Left", PORT_LEFT, (0.0, 0.8, 0.3, 0.4), invert_pitch=True)
        self.right_hand = HandModule("Right", PORT_RIGHT, (1.0, 0.2, 0.2, 0.4), invert_pitch=False)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        sections = [
            (self.left_hand.plot_gpio, self.left_hand.plot_q),
            (self.left_hand.trackball, self.left_hand.view_imu),
            (self.right_hand.trackball, self.right_hand.view_imu),
            (self.right_hand.plot_gpio, self.right_hand.plot_q)
        ]

        for widgets in sections:
            layout = QVBoxLayout()
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(30)
            layout.addWidget(widgets[0], stretch=1)
            layout.addWidget(widgets[1], stretch=1)
            main_layout.addLayout(layout, stretch=1)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_all)
        self.timer.start(16)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_R:
            self.left_hand.is_first_data = True
            self.right_hand.is_first_data = True

    def update_all(self):
        self.left_hand.process_data()
        self.right_hand.process_data()
        self.left_hand.update_plots()
        self.right_hand.update_plots()

    def closeEvent(self, event):
        if self.left_hand.serial: self.left_hand.serial.close()
        if self.right_hand.serial: self.right_hand.serial.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = DualSensorViewer()
    viewer.show()
    sys.exit(app.exec())