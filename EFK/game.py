import sys
import os
import time
import threading
import ctypes
import cv2
import numpy as np
import mss
import tkinter as tk
from tkinter import ttk, messagebox
from pynput import mouse, keyboard
import json  # 新增：用于配置持久化


# ================= 解决路径与中文编码问题 =================
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def cv2_imread_cn(file_path):
    try:
        img = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        return img
    except:
        return None


# ================= 全局配置管理 =================
class Config:
    def __init__(self):
        # 默认内置参数
        self.DEFAULT_CONFIG = {
            "confidence": 0.7,
            "cooldown": 0.3,
            "trigger_key": "x2",
            "scan_region": None
        }
        self.ICON_FILES = [
            'Snipaste_2026-04-16_22-33-32.png',
            'Snipaste_2026-04-16_22-33-43.png',
            'Snipaste_2026-04-16_22-57-57.png'
        ]
        self.config_file = "config.json"
        self.load_config()  # 启动时加载

        self.is_running = False
        self.exit_program = False
        self.is_setting_area = False
        self.is_recording_key = False
        self.temp_points = []

    def load_config(self):
        """从本地 JSON 加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.confidence = data.get("confidence", 0.7)
                    self.cooldown = data.get("cooldown", 0.3)
                    self.trigger_key = data.get("trigger_key", "x2")
                    self.scan_region = data.get("scan_region", None)
            except:
                self.reset_to_default(save=False)
        else:
            self.reset_to_default(save=True)

    def save_config(self):
        """保存当前配置到本地 JSON"""
        data = {
            "confidence": self.confidence,
            "cooldown": self.cooldown,
            "trigger_key": self.trigger_key,
            "scan_region": self.scan_region
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def reset_to_default(self, save=True):
        """恢复默认参数"""
        self.confidence = self.DEFAULT_CONFIG["confidence"]
        self.cooldown = self.DEFAULT_CONFIG["cooldown"]
        self.trigger_key = self.DEFAULT_CONFIG["trigger_key"]
        self.scan_region = self.DEFAULT_CONFIG["scan_region"]
        if save:
            self.save_config()


cfg = Config()


# ================= 底层逻辑 (点击/扫描) =================
def win32_click(x, y):
    ix, iy = int(x), int(y)
    ctypes.windll.user32.SetCursorPos(ix, iy)
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)


def scan_logic():
    templates = []
    for f in cfg.ICON_FILES:
        path = resource_path(f)
        img = cv2_imread_cn(path)
        if img is not None:
            templates.append((f, img))

    with mss.mss() as sct:
        while not cfg.exit_program:
            if cfg.is_running and templates:
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
                            time.sleep(cfg.cooldown)
                            break
                except:
                    pass
                time.sleep(0.01)
            else:
                time.sleep(0.2)


# ================= UI 界面 =================
class AppUI:
    def __init__(self, root):
        self.root = root
        self.root.title("EFK专注满级辅助")
        self.root.geometry("380x580")
        self.root.attributes("-topmost", True)
        self.setup_ui()
        self.refresh_ui()

    def setup_ui(self):
        tk.Label(self.root, text="--- 运行状态 ---", font=("微软雅黑", 9)).pack(pady=5)
        self.lbl_run = tk.Label(self.root, text="已停止", fg="red", font=("微软雅黑", 14, "bold"))
        self.lbl_run.pack()

        # 参数面板
        set_frame = tk.LabelFrame(self.root, text=" 实时参数 ")
        set_frame.pack(padx=20, pady=10, fill="x")

        tk.Label(set_frame, text="匹配精度 (0.5-0.9):").grid(row=0, column=0, padx=5, pady=5)
        self.ent_conf = tk.Entry(set_frame, width=8)
        self.ent_conf.grid(row=0, column=1)

        tk.Label(set_frame, text="点击间隔 (秒):").grid(row=1, column=0, padx=5, pady=5)
        self.ent_cool = tk.Entry(set_frame, width=8)
        self.ent_cool.grid(row=1, column=1)

        # 初始化输入框数值
        self.ent_conf.insert(0, str(cfg.confidence))
        self.ent_cool.insert(0, str(cfg.cooldown))

        ttk.Button(set_frame, text="更新并保存参数", command=self.update_cfg).grid(row=2, column=0, columnspan=2,
                                                                                   pady=5)

        # 热键面板
        key_frame = tk.LabelFrame(self.root, text=" 启动热键 ")
        key_frame.pack(padx=20, pady=5, fill="x")
        self.lbl_key = tk.Label(key_frame, text="", font=("微软雅黑", 10, "bold"))
        self.lbl_key.pack(pady=5)
        self.btn_record = ttk.Button(key_frame, text="点击修改热键", command=self.start_record_key)
        self.btn_record.pack(pady=5)

        # 范围面板
        area_frame = tk.LabelFrame(self.root, text=" 扫描区域 ")
        area_frame.pack(padx=20, pady=5, fill="x")
        self.lbl_area = tk.Label(area_frame, text="", wraplength=300, font=("微软雅黑", 9))
        self.lbl_area.pack(pady=5)
        ttk.Button(area_frame, text="设置范围 (按4次 F1)", command=self.start_area).pack(pady=2)
        ttk.Button(area_frame, text="还原全屏", command=self.reset_area).pack(pady=2)

        # 系统面板
        sys_frame = tk.LabelFrame(self.root, text=" 系统操作 ")
        sys_frame.pack(padx=20, pady=10, fill="x")
        ttk.Button(sys_frame, text="一键恢复默认设置", command=self.restore_all).pack(pady=5, fill="x")

    def update_cfg(self):
        try:
            cfg.confidence = float(self.ent_conf.get())
            cfg.cooldown = float(self.ent_cool.get())
            cfg.save_config()
            messagebox.showinfo("成功", "参数已生效并保存至本地")
        except:
            messagebox.showerror("错误", "请输入数字")

    def restore_all(self):
        if messagebox.askyesno("提示", "确定要恢复所有默认设置吗？"):
            cfg.reset_to_default()
            # 同步更新 UI 输入框
            self.ent_conf.delete(0, tk.END)
            self.ent_conf.insert(0, str(cfg.confidence))
            self.ent_cool.delete(0, tk.END)
            self.ent_cool.insert(0, str(cfg.cooldown))
            messagebox.showinfo("成功", "已恢复出厂设置")

    def start_record_key(self):
        cfg.is_recording_key = True
        self.btn_record.config(text="请按下新热键...")

    def start_area(self):
        cfg.is_setting_area = True
        cfg.temp_points = []
        messagebox.showinfo("提示", "请将鼠标移至区域4个角，每个角按一次F1")

    def reset_area(self):
        cfg.scan_region = None
        cfg.save_config()
        self.lbl_area.config(text="当前范围: 全屏")

    def refresh_ui(self):
        color = "green" if cfg.is_running else "red"
        text = "▶ 运行中" if cfg.is_running else "■ 已停止"
        self.lbl_run.config(text=text, fg=color)
        self.lbl_key.config(text=f"当前热键: {cfg.trigger_key.upper()}")
        if cfg.scan_region:
            self.lbl_area.config(text=f"自定义区域: {cfg.scan_region['width']}x{cfg.scan_region['height']}")
        else:
            self.lbl_area.config(text="当前范围: 全屏")
        if not cfg.is_recording_key:
            self.btn_record.config(text="点击修改热键")
        self.root.after(300, self.refresh_ui)


# ================= 监听逻辑 =================
def on_key_press(key):
    if cfg.is_recording_key:
        new_key = ""
        if hasattr(key, 'name'):
            new_key = key.name
        elif hasattr(key, 'char'):
            new_key = key.char
        if new_key and new_key not in ['f1', 'f12']:
            cfg.trigger_key = new_key
            cfg.is_recording_key = False
            cfg.save_config()  # 自动保存热键
        return

    if key == keyboard.Key.f1 and cfg.is_setting_area:
        x, y = mouse.Controller().position
        cfg.temp_points.append((x, y))
        if len(cfg.temp_points) >= 4:
            xs, ys = [p[0] for p in cfg.temp_points], [p[1] for p in cfg.temp_points]
            l, t, r, b = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
            cfg.scan_region = {'left': l, 'top': t, 'width': r - l, 'height': b - t}
            cfg.is_setting_area = False
            cfg.save_config()  # 自动保存区域
            messagebox.showinfo("成功", "区域锁定完成并已保存")

    if key == keyboard.Key.f12:
        cfg.exit_program = True
        return False

    curr_key = ""
    if hasattr(key, 'name'):
        curr_key = key.name
    elif hasattr(key, 'char'):
        curr_key = key.char
    if curr_key == cfg.trigger_key:
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
        cfg.is_running = not cfg.is_running


if __name__ == '__main__':
    ctypes.windll.user32.SetProcessDPIAware()
    threading.Thread(target=scan_logic, daemon=True).start()
    root = tk.Tk()
    app = AppUI(root)
    keyboard.Listener(on_press=on_key_press).start()
    mouse.Listener(on_click=on_mouse_click).start()
    root.mainloop()
    cfg.exit_program = True