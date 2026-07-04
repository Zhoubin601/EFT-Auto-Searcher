import sys
import os
import time
import threading
import ctypes
import cv2
import numpy as np
import mss
import random
from pynput import mouse, keyboard
import json
import webview

# ================= 解决路径与中文编码问题 =================
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def cv2_imread_cn(file_path):
    try:
        img = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        return img
    except:
        return None


# ================= 模拟键鼠底层操作 =================
def win32_click(x, y):
    offset_x = random.randint(-2, 2)
    offset_y = random.randint(-2, 2)
    ix, iy = int(x) + offset_x, int(y) + offset_y
    ctypes.windll.user32.SetCursorPos(ix, iy)
    time.sleep(0.05)
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)


def win32_double_click(x, y):
    """双击打开弹药页面"""
    win32_click(x, y)
    time.sleep(0.1)
    win32_click(x, y)


def win32_press_ctrl():
    """按下Ctrl键"""
    ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)


def win32_release_ctrl():
    """松开Ctrl键"""
    ctypes.windll.user32.keybd_event(0x11, 0, 0x0002, 0)


def win32_press_esc():
    """按下ESC关闭页面"""
    ctypes.windll.user32.keybd_event(0x1B, 0, 0, 0)
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(0x1B, 0, 0x0002, 0)


# ================= 全局配置管理 =================
class Config:
    def __init__(self):
        self.DEFAULT_CONFIG = {
            "confidence": 0.8,
            "cooldown": 0.1,
            "trigger_key": "v",
            "scan_region": {
                "left": 1362,
                "top": 56,
                "width": 303,
                "height": 898
            },
            "icon_files": ['搜索1.png', '叉1.png', '搜索2.png', '搜索3.png'],
            "ammo_box_start": None,
            "ammo_col_gap": 0,
            "ammo_row_gap": 0,
            "ammo_target_pos": None,
            "ammo_max_col": 7,
            "ammo_max_row": 7,
            "ammo_click_count": 1,
        }
        self.ICON_FILES = []
        self.config_file = "config.json"

        # 运行状态
        self.is_running = False
        self.exit_program = False
        self.is_setting_area = False
        self.is_recording_key = False
        self.is_setting_ammo_pos = False
        self.temp_points = []
        self.templates_need_update = True

        # 弹药批量状态
        self.is_ammo_running = False
        self.current_col = 0
        self.current_row = 0

        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.confidence = data.get("confidence", self.DEFAULT_CONFIG["confidence"])
                self.cooldown = data.get("cooldown", self.DEFAULT_CONFIG["cooldown"])
                self.trigger_key = data.get("trigger_key", self.DEFAULT_CONFIG["trigger_key"])
                self.scan_region = data.get("scan_region", self.DEFAULT_CONFIG["scan_region"])
                self.ICON_FILES = data.get("icon_files", self.DEFAULT_CONFIG["icon_files"].copy())

                self.ammo_box_start = data.get("ammo_box_start", self.DEFAULT_CONFIG["ammo_box_start"])
                self.ammo_col_gap = data.get("ammo_col_gap", self.DEFAULT_CONFIG["ammo_col_gap"])
                self.ammo_row_gap = data.get("ammo_row_gap", self.DEFAULT_CONFIG["ammo_row_gap"])
                self.ammo_target_pos = data.get("ammo_target_pos", self.DEFAULT_CONFIG["ammo_target_pos"])
                self.ammo_max_col = data.get("ammo_max_col", self.DEFAULT_CONFIG["ammo_max_col"])
                self.ammo_max_row = data.get("ammo_max_row", self.DEFAULT_CONFIG["ammo_max_row"])
                self.ammo_click_count = data.get("ammo_click_count", self.DEFAULT_CONFIG["ammo_click_count"])

                self.save_config()
            except:
                self.reset_to_default(save=True)
        else:
            self.reset_to_default(save=True)

    def save_config(self):
        data = {
            "confidence": self.confidence,
            "cooldown": self.cooldown,
            "trigger_key": self.trigger_key,
            "scan_region": self.scan_region,
            "icon_files": self.ICON_FILES,
            "ammo_box_start": self.ammo_box_start,
            "ammo_col_gap": self.ammo_col_gap,
            "ammo_row_gap": self.ammo_row_gap,
            "ammo_target_pos": self.ammo_target_pos,
            "ammo_max_col": self.ammo_max_col,
            "ammo_max_row": self.ammo_max_row,
            "ammo_click_count": self.ammo_click_count
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def reset_to_default(self, save=True):
        self.confidence = self.DEFAULT_CONFIG["confidence"]
        self.cooldown = self.DEFAULT_CONFIG["cooldown"]
        self.trigger_key = self.DEFAULT_CONFIG["trigger_key"]
        self.scan_region = self.DEFAULT_CONFIG["scan_region"]
        self.ICON_FILES = self.DEFAULT_CONFIG["icon_files"].copy()

        self.ammo_box_start = self.DEFAULT_CONFIG["ammo_box_start"]
        self.ammo_col_gap = self.DEFAULT_CONFIG["ammo_col_gap"]
        self.ammo_row_gap = self.DEFAULT_CONFIG["ammo_row_gap"]
        self.ammo_target_pos = self.DEFAULT_CONFIG["ammo_target_pos"]
        self.ammo_max_col = self.DEFAULT_CONFIG["ammo_max_col"]
        self.ammo_max_row = self.DEFAULT_CONFIG["ammo_max_row"]
        self.ammo_click_count = self.DEFAULT_CONFIG["ammo_click_count"]

        self.templates_need_update = True
        if save:
            self.save_config()


cfg = Config()

# ================= 原图像扫描逻辑 =================
def scan_logic():
    templates = []

    def load_templates():
        temps = []
        for f in cfg.ICON_FILES:
            if os.path.isabs(f) and os.path.exists(f):
                path = f
            else:
                path = resource_path(f)
            img = cv2_imread_cn(path)
            if img is not None:
                temps.append((os.path.basename(f), img))
        return temps

    with mss.mss() as sct:
        while not cfg.exit_program:
            if cfg.templates_need_update:
                templates = load_templates()
                cfg.templates_need_update = False
            if cfg.is_running and templates and not cfg.is_ammo_running:
                monitor = cfg.scan_region if cfg.scan_region else sct.monitors[1]
                try:
                    screenshot = np.array(sct.grab(monitor))
                    screen_bgr = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
                    for name, temp in templates:
                        res = cv2.matchTemplate(screen_bgr, temp, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, max_loc = cv2.minMaxLoc(res)
                        if max_val >= cfg.confidence:
                            h, w = temp.shape[:2]
                            offset_x = cfg.scan_region['left'] if cfg.scan_region else 0
                            offset_y = cfg.scan_region['top'] if cfg.scan_region else 0
                            win32_click(max_loc[0] + w // 2 + offset_x, max_loc[1] + h // 2 + offset_y)
                            human_delay = random.uniform(0.01, 0.05)
                            time.sleep(cfg.cooldown + human_delay)
                            break
                except:
                    pass
                time.sleep(0.01)
            else:
                time.sleep(0.2)


# ================= 弹药箱批量装填逻辑 =================
def ammo_batch_logic():
    while not cfg.exit_program:
        if not cfg.is_ammo_running:
            time.sleep(0.2)
            continue

        if not cfg.ammo_box_start or not cfg.ammo_target_pos or cfg.ammo_col_gap == 0 or cfg.ammo_row_gap == 0:
            cfg.is_ammo_running = False
            continue

        try:
            for row in range(cfg.ammo_max_row):
                if not cfg.is_ammo_running: break
                cfg.current_row = row
                for col in range(cfg.ammo_max_col):
                    if not cfg.is_ammo_running: break
                    cfg.current_col = col

                    box_x = cfg.ammo_box_start[0] + col * cfg.ammo_col_gap
                    box_y = cfg.ammo_box_start[1] + row * cfg.ammo_row_gap

                    win32_double_click(box_x, box_y)
                    time.sleep(0.3)

                    win32_press_ctrl()
                    time.sleep(0.1)
                    for _ in range(cfg.ammo_click_count):
                        if not cfg.is_ammo_running: break
                        win32_click(cfg.ammo_target_pos[0], cfg.ammo_target_pos[1])
                        time.sleep(0.2)

                    win32_release_ctrl()
                    time.sleep(0.1)

                    win32_press_esc()
                    time.sleep(0.3)

            if cfg.is_ammo_running:
                cfg.is_ammo_running = False
        except Exception as e:
            cfg.is_ammo_running = False
        time.sleep(0.2)


# ================= PyWebView API =================
class Api:
    def __init__(self):
        self.window = None

    def get_state(self):
        return {
            "is_running": cfg.is_running,
            "trigger_key": cfg.trigger_key,
            "scan_region": cfg.scan_region,
            "is_recording_key": cfg.is_recording_key,
            "is_setting_area": cfg.is_setting_area,
            "is_setting_ammo_pos": cfg.is_setting_ammo_pos,
            "is_ammo_running": cfg.is_ammo_running,
            "ammo_box_start": cfg.ammo_box_start,
            "ammo_col_gap": cfg.ammo_col_gap,
            "ammo_row_gap": cfg.ammo_row_gap,
            "ammo_target_pos": cfg.ammo_target_pos,
            "confidence": cfg.confidence,
            "cooldown": cfg.cooldown,
            "ammo_click_count": cfg.ammo_click_count,
            "icon_files": cfg.ICON_FILES
        }

    def update_cfg(self, confidence, cooldown):
        try:
            cfg.confidence = float(confidence)
            cfg.cooldown = float(cooldown)
            cfg.save_config()
        except ValueError:
            pass

    def start_record_key(self):
        cfg.is_recording_key = True

    def start_area(self):
        cfg.is_setting_area = True
        cfg.temp_points = []

    def reset_area(self):
        cfg.scan_region = None
        cfg.save_config()

    def toggle_ammo_pos_setting(self):
        cfg.is_setting_ammo_pos = not cfg.is_setting_ammo_pos

    def save_ammo_count(self, count):
        try:
            val = int(count)
            if val >= 1:
                cfg.ammo_click_count = val
                cfg.save_config()
        except ValueError:
            pass

    def start_ammo_batch(self):
        if cfg.ammo_box_start and cfg.ammo_target_pos and cfg.ammo_col_gap != 0 and cfg.ammo_row_gap != 0:
            cfg.is_ammo_running = True
            cfg.is_running = False

    def stop_ammo_batch(self):
        cfg.is_ammo_running = False

    def add_image(self):
        file_types = ('Image files (*.png;*.jpg;*.jpeg;*.bmp)', 'All files (*.*)')
        result = self.window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
        if result and len(result) > 0:
            filepath = result[0]
            if filepath not in cfg.ICON_FILES:
                cfg.ICON_FILES.append(filepath)
                cfg.save_config()
                cfg.templates_need_update = True

    def remove_image(self, index):
        if 0 <= index < len(cfg.ICON_FILES):
            cfg.ICON_FILES.pop(index)
            cfg.save_config()
            cfg.templates_need_update = True

    def restore_all(self):
        cfg.reset_to_default()

    def exit_program(self):
        cfg.exit_program = True
        self.window.destroy()
        os._exit(0)


# ================= 键鼠监听 =================
def on_key_press(key):
    if cfg.is_recording_key:
        new_key = ""
        if hasattr(key, 'name'):
            new_key = key.name
        elif hasattr(key, 'char'):
            new_key = key.char
        if new_key and new_key not in ['f1', 'f2', 'f3', 'f4', 'f5', 'f11', 'f12']:
            cfg.trigger_key = new_key
            cfg.is_recording_key = False
            cfg.save_config()
        return

    if key == keyboard.Key.f1:
        if cfg.is_setting_area:
            x, y = mouse.Controller().position
            cfg.temp_points.append((x, y))
            if len(cfg.temp_points) >= 4:
                xs, ys = [p[0] for p in cfg.temp_points], [p[1] for p in cfg.temp_points]
                l, t, r, b = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
                cfg.scan_region = {'left': l, 'top': t, 'width': r - l, 'height': b - t}
                cfg.is_setting_area = False
                cfg.save_config()
        elif cfg.is_setting_ammo_pos:
            x, y = mouse.Controller().position
            cfg.ammo_box_start = (x, y)
            cfg.save_config()

    if key == keyboard.Key.f2:
        if cfg.is_setting_ammo_pos and cfg.ammo_box_start:
            x, y = mouse.Controller().position
            cfg.ammo_col_gap = x - cfg.ammo_box_start[0]
            cfg.save_config()

    if key == keyboard.Key.f3:
        if cfg.is_setting_ammo_pos and cfg.ammo_box_start:
            x, y = mouse.Controller().position
            cfg.ammo_row_gap = y - cfg.ammo_box_start[1]
            cfg.save_config()

    if key == keyboard.Key.f4:
        if cfg.is_setting_ammo_pos:
            x, y = mouse.Controller().position
            cfg.ammo_target_pos = (x, y)
            cfg.save_config()
            cfg.is_setting_ammo_pos = False

    if key == keyboard.Key.f5:
        if cfg.ammo_box_start and cfg.ammo_target_pos and cfg.ammo_col_gap != 0 and cfg.ammo_row_gap != 0:
            cfg.is_ammo_running = True
            cfg.is_running = False

    if key == keyboard.Key.f12:
        cfg.is_ammo_running = False

    if key == keyboard.Key.f11:
        cfg.exit_program = True
        os._exit(0)
        return False

    curr_key = ""
    if hasattr(key, 'name'):
        curr_key = key.name
    elif hasattr(key, 'char'):
        curr_key = key.char
    if curr_key == cfg.trigger_key:
        if not cfg.is_ammo_running:
            cfg.is_running = not cfg.is_running


def on_mouse_click(x, y, button, pressed):
    if not pressed: return
    btn_name = str(button).split('.')[-1].lower()
    if cfg.is_recording_key:
        if btn_name in ['x1', 'x2', 'middle']:
            cfg.trigger_key = btn_name
            cfg.is_recording_key = False
            cfg.save_config()
        return
    if btn_name == cfg.trigger_key:
        if not cfg.is_ammo_running:
            cfg.is_running = not cfg.is_running


def on_startup(window):
    # 启动后台线程
    threading.Thread(target=scan_logic, daemon=True).start()
    threading.Thread(target=ammo_batch_logic, daemon=True).start()
    
    # 启动键鼠监听
    keyboard.Listener(on_press=on_key_press).start()
    mouse.Listener(on_click=on_mouse_click).start()

if __name__ == '__main__':
    ctypes.windll.user32.SetProcessDPIAware()
    
    # 初始化 PyWebView
    api = Api()
    window = webview.create_window('EFT Auto Searcher', 'http://localhost:5173', width=710, height=600)
    api.window = window
    
    window.expose(api.get_state, api.update_cfg, api.start_record_key, api.start_area, api.reset_area,
                  api.toggle_ammo_pos_setting, api.save_ammo_count, api.start_ammo_batch, api.stop_ammo_batch,
                  api.add_image, api.remove_image, api.restore_all, api.exit_program)
    
    # 使用 Edge Chromium 渲染，并在窗口准备好后启动后台线程
    webview.start(on_startup, window, gui='edgechromium', debug=True)
    
    # 窗口关闭后清理
    cfg.exit_program = True