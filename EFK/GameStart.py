import sys
import os
import time
import threading
import ctypes
import cv2
import numpy as np
import mss
import tkinter as tk
import random
from tkinter import ttk, messagebox, filedialog
from pynput import mouse, keyboard
import json


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
            # 弹药批量配置
            "ammo_box_start": None,
            "ammo_col_gap": 0,
            "ammo_row_gap": 0,
            "ammo_target_pos": None,
            "ammo_max_col": 7,
            "ammo_max_row": 7,
            "ammo_click_count": 1,  # 每个弹药箱点击次数
        }
        self.ICON_FILES = []
        self.config_file = "config.json"

        # 运行状态 (不需要保存到json里的状态变量)
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

        # 初始化时执行加载
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 原配置 (如果json里没有，就用DEFAULT_CONFIG里的默认值)
                self.confidence = data.get("confidence", self.DEFAULT_CONFIG["confidence"])
                self.cooldown = data.get("cooldown", self.DEFAULT_CONFIG["cooldown"])
                self.trigger_key = data.get("trigger_key", self.DEFAULT_CONFIG["trigger_key"])
                self.scan_region = data.get("scan_region", self.DEFAULT_CONFIG["scan_region"])
                self.ICON_FILES = data.get("icon_files", self.DEFAULT_CONFIG["icon_files"].copy())

                # 弹药配置自动补全兼容
                self.ammo_box_start = data.get("ammo_box_start", self.DEFAULT_CONFIG["ammo_box_start"])
                self.ammo_col_gap = data.get("ammo_col_gap", self.DEFAULT_CONFIG["ammo_col_gap"])
                self.ammo_row_gap = data.get("ammo_row_gap", self.DEFAULT_CONFIG["ammo_row_gap"])
                self.ammo_target_pos = data.get("ammo_target_pos", self.DEFAULT_CONFIG["ammo_target_pos"])
                self.ammo_max_col = data.get("ammo_max_col", self.DEFAULT_CONFIG["ammo_max_col"])
                self.ammo_max_row = data.get("ammo_max_row", self.DEFAULT_CONFIG["ammo_max_row"])
                self.ammo_click_count = data.get("ammo_click_count", self.DEFAULT_CONFIG["ammo_click_count"])

                # 成功读取后，立刻保存一次。这样旧版 json 就会自动被加上新增的字段，完成无缝升级
                self.save_config()
            except:
                # 哪怕 json 格式彻底坏了，也能安全降级生成全新的
                self.reset_to_default(save=True)
        else:
            # 没有 json 文件时，生成全新的
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
    """弹药箱7×7循环批量装填核心流程"""
    while not cfg.exit_program:
        if not cfg.is_ammo_running:
            time.sleep(0.2)
            continue

        # 校验配置
        if not cfg.ammo_box_start or not cfg.ammo_target_pos or cfg.ammo_col_gap == 0 or cfg.ammo_row_gap == 0:
            messagebox.showerror("错误", "请先点击开启坐标设置，通过F1-F4完成所有位置设置！")
            cfg.is_ammo_running = False
            continue

        # 循环遍历7行7列
        try:
            for row in range(cfg.ammo_max_row):
                if not cfg.is_ammo_running: break
                cfg.current_row = row
                for col in range(cfg.ammo_max_col):
                    if not cfg.is_ammo_running: break
                    cfg.current_col = col

                    # 1. 计算当前弹药箱坐标
                    box_x = cfg.ammo_box_start[0] + col * cfg.ammo_col_gap
                    box_y = cfg.ammo_box_start[1] + row * cfg.ammo_row_gap

                    # 2. 双击打开弹药页面
                    win32_double_click(box_x, box_y)
                    time.sleep(0.3)

                    # 3. 按住Ctrl + 循环点击弹药位置（自定义次数）
                    win32_press_ctrl()
                    time.sleep(0.1)
                    for _ in range(cfg.ammo_click_count):
                        if not cfg.is_ammo_running: break
                        win32_click(cfg.ammo_target_pos[0], cfg.ammo_target_pos[1])
                        time.sleep(0.2)

                    # 4. 松开Ctrl
                    win32_release_ctrl()
                    time.sleep(0.1)

                    # 5. ESC关闭弹药页面
                    win32_press_esc()
                    time.sleep(0.3)

            # 全部完成
            if cfg.is_ammo_running:  # 只有在自然完成时才弹窗，被主动停止时不弹
                cfg.is_ammo_running = False
                messagebox.showinfo("完成", "所有7×7弹药箱已装填完毕！")
        except Exception as e:
            cfg.is_ammo_running = False
            messagebox.showerror("异常", f"批量装填出错：{str(e)}")
        time.sleep(0.2)


# ================= UI界面 =================
class AppUI:
    def __init__(self, root):
        self.root = root
        self.root.title("EFT")
        self.root.geometry("420x870")  # 稍微拉长了一点，给新增的文字腾出空间
        self.root.attributes("-topmost", False)
        self.setup_ui()
        self.refresh_ui()

    def setup_ui(self):
        # 运行状态
        tk.Label(self.root, text="--- 运行状态 ---", font=("微软雅黑", 9)).pack(pady=5)
        self.lbl_run = tk.Label(self.root, text="已停止", fg="red", font=("微软雅黑", 14, "bold"))
        self.lbl_run.pack()

        # 参数设置
        set_frame = tk.LabelFrame(self.root, text=" 实时参数 ")
        set_frame.pack(padx=20, pady=5, fill="x")
        tk.Label(set_frame, text="匹配精度 (0.5-0.9):").grid(row=0, column=0, padx=5, pady=5)
        self.ent_conf = tk.Entry(set_frame, width=8)
        self.ent_conf.grid(row=0, column=1)
        tk.Label(set_frame, text="点击间隔 (秒):").grid(row=1, column=0, padx=5, pady=5)
        self.ent_cool = tk.Entry(set_frame, width=8)
        self.ent_cool.grid(row=1, column=1)
        self.ent_conf.insert(0, str(cfg.confidence))
        self.ent_cool.insert(0, str(cfg.cooldown))
        ttk.Button(set_frame, text="更新并保存参数", command=self.update_cfg).grid(row=2, column=0, columnspan=2,
                                                                                   pady=5)

        # 快捷操作
        op_frame = tk.LabelFrame(self.root, text=" 快捷操作 ")
        op_frame.pack(padx=20, pady=5, fill="x")
        self.lbl_key = tk.Label(op_frame, text="", font=("微软雅黑", 9, "bold"))
        self.lbl_key.pack(pady=2)
        self.btn_record = ttk.Button(op_frame, text="点击修改启动热键", command=self.start_record_key)
        self.btn_record.pack(pady=2)
        self.lbl_area = tk.Label(op_frame, text="", wraplength=300, font=("微软雅黑", 9))
        self.lbl_area.pack(pady=2)
        area_btn_frame = tk.Frame(op_frame)
        area_btn_frame.pack(pady=2)
        ttk.Button(area_btn_frame, text="设范围(4次F1)", command=self.start_area).pack(side="left", padx=2)
        ttk.Button(area_btn_frame, text="还原全屏", command=self.reset_area).pack(side="left", padx=2)

        # ================= 弹药批量操作模块 =================
        ammo_frame = tk.LabelFrame(self.root, text=" 弹药箱批量装填（7×7循环） ")
        ammo_frame.pack(padx=20, pady=8, fill="x")

        # 弹药状态
        self.lbl_ammo_status = tk.Label(ammo_frame, text="弹药批量：未运行", fg="red", font=("微软雅黑", 10, "bold"))
        self.lbl_ammo_status.pack(pady=3)

        # 当前位置信息
        self.lbl_ammo_pos = tk.Label(ammo_frame, text="", wraplength=350, font=("微软雅黑", 8))
        self.lbl_ammo_pos.pack(pady=2)

        # 弹药点击次数设置
        count_frame = tk.Frame(ammo_frame)
        count_frame.pack(pady=5)
        tk.Label(count_frame, text="每个弹药箱放弹药次数：", font=("微软雅黑", 9)).pack(side="left", padx=3)
        self.ent_ammo_count = tk.Entry(count_frame, width=5)
        self.ent_ammo_count.pack(side="left")
        self.ent_ammo_count.insert(0, str(cfg.ammo_click_count))
        ttk.Button(count_frame, text="保存", command=self.save_ammo_count).pack(side="left", padx=3)

        # 坐标设置开关控制
        self.btn_toggle_ammo_pos = ttk.Button(ammo_frame, text="开启坐标设置 (F1-F4)",
                                              command=self.toggle_ammo_pos_setting)
        self.btn_toggle_ammo_pos.pack(pady=5)

        # 按键说明
        tk.Label(ammo_frame, text="需开启上方设置后，以下快捷键才生效：", font=("微软雅黑", 8)).pack()
        tk.Label(ammo_frame, text="【F1】第一个弹药箱位置", font=("微软雅黑", 8), fg="blue").pack()
        tk.Label(ammo_frame, text="【F2】横向间距（点右侧弹药箱）", font=("微软雅黑", 8), fg="blue").pack()
        tk.Label(ammo_frame, text="【F3】纵向间距（点下排第一个）", font=("微软雅黑", 8), fg="blue").pack()
        tk.Label(ammo_frame, text="【F4】右上角弹药放置位置", font=("微软雅黑", 8), fg="blue").pack()

        tk.Label(ammo_frame, text=" ", font=("微软雅黑", 2)).pack()  # 垫一点间距

        # 控制按钮
        ammo_btn_frame = tk.Frame(ammo_frame)
        ammo_btn_frame.pack(pady=5)
        self.btn_ammo_start = ttk.Button(ammo_btn_frame, text="启动弹药批量 (F5)", command=self.start_ammo_batch)
        self.btn_ammo_start.pack(side="left", padx=3)
        ttk.Button(ammo_btn_frame, text="停止弹药批量 (F12)", command=self.stop_ammo_batch).pack(side="left", padx=3)

        tk.Label(ammo_frame, text="【F5】启动弹药批量循环", font=("微软雅黑", 8), fg="green").pack(pady=2)
        tk.Label(ammo_frame, text="【F12】立即停止批量循环", font=("微软雅黑", 8), fg="red").pack(pady=2)
        tk.Label(ammo_frame, text="【F11】完全退出整个程序", font=("微软雅黑", 8), fg="red").pack()

        # 图片管理
        img_frame = tk.LabelFrame(self.root, text=" 图片管理 (自动保存) ")
        img_frame.pack(padx=20, pady=5, fill="x")
        scroll = tk.Scrollbar(img_frame)
        scroll.pack(side="right", fill="y", pady=5)
        self.listbox_imgs = tk.Listbox(img_frame, height=4, yscrollcommand=scroll.set, font=("微软雅黑", 8))
        self.listbox_imgs.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scroll.config(command=self.listbox_imgs.yview)
        self.refresh_listbox()
        btn_frame = tk.Frame(img_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)
        ttk.Button(btn_frame, text="添加外部图片", command=self.add_image).pack(side="left", expand=True, fill="x",
                                                                                padx=2)
        ttk.Button(btn_frame, text="删除选中图片", command=self.remove_image).pack(side="left", expand=True, fill="x",
                                                                                   padx=2)

        # 系统设置
        sys_frame = tk.Frame(self.root)
        sys_frame.pack(padx=20, pady=10, fill="x")
        ttk.Button(sys_frame, text="一键恢复所有默认设置", command=self.restore_all).pack(fill="x")

    def toggle_ammo_pos_setting(self):
        cfg.is_setting_ammo_pos = not cfg.is_setting_ammo_pos
        if cfg.is_setting_ammo_pos:
            messagebox.showinfo("提示", "已开启坐标录入模式！\n请将鼠标移至对应位置并按下 F1~F4。")

    # 保存弹药点击次数
    def save_ammo_count(self):
        try:
            count = int(self.ent_ammo_count.get())
            if count < 1:
                messagebox.showerror("错误", "次数必须大于等于1！")
                return
            cfg.ammo_click_count = count
            cfg.save_config()
            messagebox.showinfo("成功", f"已设置每个弹药箱点击 {count} 次")
        except:
            messagebox.showerror("错误", "请输入正整数！")

    def start_ammo_batch(self):
        cfg.is_ammo_running = True
        cfg.is_running = False

    def stop_ammo_batch(self):
        cfg.is_ammo_running = False

    def refresh_listbox(self):
        self.listbox_imgs.delete(0, tk.END)
        for f in cfg.ICON_FILES:
            self.listbox_imgs.insert(tk.END, os.path.basename(f))

    def add_image(self):
        filepath = filedialog.askopenfilename(title="选择要识别的图片",
                                              filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
        if filepath:
            if filepath not in cfg.ICON_FILES:
                cfg.ICON_FILES.append(filepath)
                cfg.save_config()
                cfg.templates_need_update = True
                self.refresh_listbox()

    def remove_image(self):
        sel = self.listbox_imgs.curselection()
        if sel:
            idx = sel[0]
            cfg.ICON_FILES.pop(idx)
            cfg.save_config()
            cfg.templates_need_update = True
            self.refresh_listbox()
        else:
            messagebox.showwarning("提示", "请先在列表中选中要删除的图片")

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
            self.ent_conf.delete(0, tk.END)
            self.ent_conf.insert(0, str(cfg.confidence))
            self.ent_cool.delete(0, tk.END)
            self.ent_cool.insert(0, str(cfg.cooldown))
            self.ent_ammo_count.delete(0, tk.END)
            self.ent_ammo_count.insert(0, str(cfg.ammo_click_count))
            self.refresh_listbox()
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
        # 基础状态刷新
        color = "green" if cfg.is_running else "red"
        text = "▶ 运行中" if cfg.is_running else "■ 已停止"
        self.lbl_run.config(text=text, fg=color)
        self.lbl_key.config(text=f"当前热键: {cfg.trigger_key.upper()}")
        if cfg.scan_region:
            self.lbl_area.config(text=f"自定义区域: {cfg.scan_region['width']}x{cfg.scan_region['height']}")
        else:
            self.lbl_area.config(text="当前范围: 全屏")
        if not cfg.is_recording_key:
            self.btn_record.config(text="点击修改启动热键")

        # 坐标设置按钮状态刷新
        if cfg.is_setting_ammo_pos:
            self.btn_toggle_ammo_pos.config(text="坐标设置中... (点击关闭)", style="TButton")
        else:
            self.btn_toggle_ammo_pos.config(text="开启坐标设置 (F1-F4)")

        # 弹药状态
        ammo_color = "green" if cfg.is_ammo_running else "red"
        ammo_text = "▶ 批量运行中" if cfg.is_ammo_running else "■ 批量未运行"
        self.lbl_ammo_status.config(text=ammo_text, fg=ammo_color)

        # 位置信息
        pos_text = f"起始箱:{cfg.ammo_box_start} | 横距:{cfg.ammo_col_gap} | 纵距:{cfg.ammo_row_gap} | 弹药位:{cfg.ammo_target_pos}"
        self.lbl_ammo_pos.config(text=pos_text)

        self.root.after(300, self.refresh_ui)


# ================= 键鼠监听（最终修正版） =================
def on_key_press(key):
    if cfg.is_recording_key:
        new_key = ""
        if hasattr(key, 'name'):
            new_key = key.name
        elif hasattr(key, 'char'):
            new_key = key.char
        # 排除了新增的 F5 键，避免被录制为普通热键
        if new_key and new_key not in ['f1', 'f2', 'f3', 'f4', 'f5', 'f11', 'f12']:
            cfg.trigger_key = new_key
            cfg.is_recording_key = False
            cfg.save_config()
        return

    # F1：设置扫描区域 / 第一个弹药箱
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
                messagebox.showinfo("成功", "区域锁定完成")
        elif cfg.is_setting_ammo_pos:
            x, y = mouse.Controller().position
            cfg.ammo_box_start = (x, y)
            cfg.save_config()
            messagebox.showinfo("成功", f"已设置第一个弹药箱：({x},{y})")

    # F2：横向间距
    if key == keyboard.Key.f2:
        if cfg.is_setting_ammo_pos:
            if cfg.ammo_box_start:
                x, y = mouse.Controller().position
                cfg.ammo_col_gap = x - cfg.ammo_box_start[0]
                cfg.save_config()
                messagebox.showinfo("成功", f"横向间距：{cfg.ammo_col_gap} 像素")
            else:
                messagebox.showwarning("提示", "先按F1设置起始箱！")

    # F3：纵向间距
    if key == keyboard.Key.f3:
        if cfg.is_setting_ammo_pos:
            if cfg.ammo_box_start:
                x, y = mouse.Controller().position
                cfg.ammo_row_gap = y - cfg.ammo_box_start[1]
                cfg.save_config()
                messagebox.showinfo("成功", f"纵向间距：{cfg.ammo_row_gap} 像素")
            else:
                messagebox.showwarning("提示", "先按F1设置起始箱！")

    # F4：弹药放置位置
    if key == keyboard.Key.f4:
        if cfg.is_setting_ammo_pos:
            x, y = mouse.Controller().position
            cfg.ammo_target_pos = (x, y)
            cfg.save_config()
            cfg.is_setting_ammo_pos = False
            messagebox.showinfo("成功", f"已设置弹药位置：({x},{y})\n（坐标设置模式已自动关闭）")

    # F5 = 启动弹药批量循环
    if key == keyboard.Key.f5:
        # 为了避免报错，增加条件检测：坐标必须设好才能启动
        if not cfg.ammo_box_start or not cfg.ammo_target_pos or cfg.ammo_col_gap == 0 or cfg.ammo_row_gap == 0:
            pass  # 可以在此处加弹窗，但会打断键盘监听线程，直接忽略即可，UI上会有相应报错拦截
        else:
            cfg.is_ammo_running = True
            cfg.is_running = False

    # F12 = 直接停止弹药批量循环
    if key == keyboard.Key.f12:
        cfg.is_ammo_running = False

    # F11 = 完全退出程序（关闭窗口+结束所有线程）
    if key == keyboard.Key.f11:
        cfg.exit_program = True
        try:
            root.quit()
            root.destroy()
        except:
            pass
        os._exit(0)
        return False

    # 原触发键
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


if __name__ == '__main__':
    ctypes.windll.user32.SetProcessDPIAware()
    threading.Thread(target=scan_logic, daemon=True).start()
    threading.Thread(target=ammo_batch_logic, daemon=True).start()
    root = tk.Tk()
    app = AppUI(root)
    keyboard.Listener(on_press=on_key_press).start()
    mouse.Listener(on_click=on_mouse_click).start()
    root.mainloop()
    cfg.exit_program = True