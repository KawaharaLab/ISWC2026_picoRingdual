import sys
import serial
import numpy as np
import time
from collections import deque
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QMessageBox
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
import pyqtgraph as pg

# ---------------------- ⭐️ここを編集する⭐️ ----------------------
SERIAL_PORT = "/dev/cu.usbmodem11101"  # ポート番号に合わせて変更
BAUD_RATE = 115200
# -------------------------------------------------------------

HISTORY_LEN = 100
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
pg.setConfigOptions(antialias=True)

class SensorViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NFC Monitor - Normal Mode")
        self.resize(1000, 800)
        self.setStyleSheet("background-color: white;")

        # データ管理
        self.q_history = [deque([0]*HISTORY_LEN, maxlen=HISTORY_LEN) for _ in range(4)]
        # インデックス対応: 0:L, 1:R, 2:U, 3:D, 4:P (元のビット順を保持しつつ描画で並び替え)
        self.gpio_history = [deque([0]*HISTORY_LEN, maxlen=HISTORY_LEN) for _ in range(5)]
        
        self.is_first_data = True
        self.prev_press = False
        self.scroll_ignore_until = 0.0
        self.cheat_mode = 0 

        # UI構築
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(30)

        self.plot_gpio = pg.PlotWidget()
        layout.addWidget(self.plot_gpio)
        
        self.plot_q = pg.PlotWidget()
        layout.addWidget(self.plot_q)

        self.setup_plots()

        try:
            self.serial = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.01)
            print(f"Connected to {SERIAL_PORT}")
        except Exception as e:
            QMessageBox.critical(self, "Serial Error", f"Could not open {SERIAL_PORT}\n{e}")
            self.serial = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_all)
        self.timer.start(16)

    def setup_plots(self):
        # フォント設定
        title_style = {'color': '#000', 'size': '20pt', 'bold': True}
        axis_font = QFont("Arial", 16, QFont.Weight.Bold) # 軸の数字を大きく

        # --- GPIO Plot (順序変更) ---
        self.plot_gpio.setTitle("Digital Input", **title_style)
        self.plot_gpio.setYRange(-0.5, 5) # 5項目(0~4)
        self.plot_gpio.showGrid(x=True, y=True, alpha=0.3)
        
        y_axis_gpio = self.plot_gpio.getAxis('left')
        y_axis_gpio.setTickFont(axis_font)
        # 上から Press, Up, Right, Down, Left の順にラベルを配置
        # Y=4:Press, Y=3:Up, Y=2:Right, Y=1:Down, Y=0:Left
        ticks = [(4.4, "PRESS"), (3.4, "UP"), (2.4, "RIGHT"), (1.4, "DOWN"), (0.4, "LEFT")]
        y_axis_gpio.setTicks([ticks])
        
        # 色設定 (L, R, U, D, P の順)
        # 描画位置調整用のインデックス配列
        self.draw_order = [0, 1, 2, 3, 4] # Left=0, Right=1, Up=2, Down=3, Press=4
        colors = ['#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4']
        self.curves_gpio = [self.plot_gpio.plot(pen=pg.mkPen(c, width=5)) for c in colors]

        # --- Quaternion Plot ---
        self.plot_q.setTitle("Quaternion", **title_style)
        self.plot_q.setYRange(-1.1, 1.1)
        self.plot_q.showGrid(x=True, y=True, alpha=0.3)
        self.plot_q.getAxis('left').setTickFont(axis_font)
        
        q_colors = ['#000000', '#ff0000', '#00ff00', '#0000ff']
        self.curves_q = [self.plot_q.plot(pen=pg.mkPen(q_colors[i], width=3)) for i in range(4)]

    def update_all(self):
        if not self.serial or not self.serial.is_open: return
        
        while self.serial.in_waiting:
            try:
                line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith("IMU:"):
                    vals = line.split(":")[1].split(",")
                    if len(vals) >= 5:
                        raw_q = [float(v) for v in vals[:4]]
                        gpio_byte = int(vals[4])
                        
                        now = time.monotonic()
                        current_press = (gpio_byte >> 4) & 1
                        if self.prev_press and not current_press:
                            self.scroll_ignore_until = now + 0.3
                        
                        filtered_gpio = gpio_byte
                        if current_press or (now < self.scroll_ignore_until):
                            filtered_gpio = gpio_byte & (1 << 4)
                        self.prev_press = current_press

                        # チートフィルタリング (1:Up, 2:Right, 3:Down, 4:Left, 5:Press)
                        if self.cheat_mode != 0:
                            mask = 0
                            if self.cheat_mode == 1: mask = (1 << 2) # Up
                            elif self.cheat_mode == 2: mask = (1 << 1) # Right
                            elif self.cheat_mode == 3: mask = (1 << 3) # Down
                            elif self.cheat_mode == 4: mask = (1 << 0) # Left
                            elif self.cheat_mode == 5: mask = (1 << 4) # Press
                            filtered_gpio &= mask
                        
                        for i in range(4): self.q_history[i].append(raw_q[i])
                        for i in range(5): self.gpio_history[i].append((filtered_gpio >> i) & 1)

            except Exception: pass

        # 描画更新 (Y軸の高さを指定の順序にオフセット)
        # 0:Left(Y=0), 1:Right(Y=2), 2:Up(Y=3), 3:Down(Y=1), 4:Press(Y=4)
        y_offsets = [0, 2, 3, 1, 4] 
        for i in range(5):
            self.curves_gpio[i].setData([(v * 0.8) + y_offsets[i] for v in self.gpio_history[i]])
        
        for i in range(4):
            self.curves_q[i].setData(list(self.q_history[i]))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_R:
            self.is_first_data = True
            print("Reset")
        
        # モード切替
        modes = {
            Qt.Key.Key_1: (1, ""),
            Qt.Key.Key_2: (2, ""),
            Qt.Key.Key_3: (3, ""),
            Qt.Key.Key_4: (4, ""),
            Qt.Key.Key_5: (5, ""),
            Qt.Key.Key_Space: (0, "")
        }

        if event.key() in modes:
            self.cheat_mode, mode_name = modes[event.key()]
            self.setWindowTitle(f"NFC Monitor - {mode_name}")
            print(f"Switched to {mode_name}")

    def closeEvent(self, event):
        if self.serial: self.serial.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = SensorViewer()
    viewer.show()
    sys.exit(app.exec())