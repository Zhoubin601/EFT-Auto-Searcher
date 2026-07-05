import os
import json
import time
import threading
import ctypes
import cv2
import numpy as np
import mss

# 全局外设锁，防止并发任务冲突
input_lock = threading.Lock()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLOWS_DIR = os.path.join(BASE_DIR, "flows")

if not os.path.exists(FLOWS_DIR):
    os.makedirs(FLOWS_DIR)

def win32_mouse_move(x, y):
    with input_lock:
        ctypes.windll.user32.SetCursorPos(int(x), int(y))

def win32_click(button="left", modifier="none"):
    with input_lock:
        if modifier == "ctrl":
            ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)
            time.sleep(0.05)
        elif modifier == "shift":
            ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)
            time.sleep(0.05)

        if button == "left":
            ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
        elif button == "right":
            ctypes.windll.user32.mouse_event(0x0008, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(0x0010, 0, 0, 0, 0)

        if modifier == "ctrl":
            ctypes.windll.user32.keybd_event(0x11, 0, 0x0002, 0)
        elif modifier == "shift":
            ctypes.windll.user32.keybd_event(0x10, 0, 0x0002, 0)

# Windows 虚拟键码映射简版
VK_MAP = {
    'esc': 0x1B, 'enter': 0x0D, 'space': 0x20, 'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44,
    'e': 0x45, 'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C,
    'm': 0x4D, 'n': 0x4E, 'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54,
    'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59, 'z': 0x5A
}

def win32_key_press(key):
    vk = VK_MAP.get(str(key).lower(), 0)
    if vk != 0:
        with input_lock:
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.05)
            ctypes.windll.user32.keybd_event(vk, 0, 0x0002, 0)

def cv2_imread_cn(file_path):
    try:
        img = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        return img
    except:
        return None

# ================= 动作模块基类与实现 =================
class Action:
    def execute(self, context, flow_state):
        pass

class ActionSleep(Action):
    def __init__(self, step_data):
        self.duration = step_data.get("duration", 1000)
    def execute(self, context, flow_state):
        if not flow_state['running']: return
        time.sleep(self.duration / 1000.0)

class ActionMouseMove(Action):
    def __init__(self, step_data):
        self.x = step_data.get("x", 0)
        self.y = step_data.get("y", 0)
    def execute(self, context, flow_state):
        if not flow_state['running']: return
        win32_mouse_move(self.x, self.y)

class ActionMouseClick(Action):
    def __init__(self, step_data):
        self.button = step_data.get("button", "left")
        self.modifier = step_data.get("modifier", "none")
    def execute(self, context, flow_state):
        if not flow_state['running']: return
        win32_click(self.button, self.modifier)

class ActionKeyPress(Action):
    def __init__(self, step_data):
        self.key = step_data.get("key", "esc")
    def execute(self, context, flow_state):
        if not flow_state['running']: return
        win32_key_press(self.key)

class ActionImageSearch(Action):
    def __init__(self, step_data):
        self.search_type = step_data.get("search_type", "single")
        self.target = step_data.get("target", "")
        self.confidence = step_data.get("confidence", 0.8)
        self.click_after_search = step_data.get("click_after_search", "none")
        
    def execute(self, context, flow_state):
        if not flow_state['running']: return
        # 默认失败
        context['last_search_success'] = False
        if not self.target:
            return

        target_paths = []
        if self.search_type == "lib":
            lib_path = os.path.join(BASE_DIR, "AutoGraph", self.target)
            if os.path.exists(lib_path) and os.path.isdir(lib_path):
                for f in os.listdir(lib_path):
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                        target_paths.append(os.path.join(lib_path, f))
        else:
            p = self.target
            if not os.path.isabs(p):
                p = os.path.join(BASE_DIR, p)
            target_paths.append(p)

        if not target_paths:
            return

        templates = []
        for p in target_paths:
            img = cv2_imread_cn(p)
            if img is not None:
                templates.append(img)
                
        if not templates:
            return

        with mss.mss() as sct:
            monitor = sct.monitors[1] # 默认主屏幕
            screenshot = np.array(sct.grab(monitor))
            screen_bgr = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
            
            for template in templates:
                if not flow_state['running']: break
                res = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                
                if max_val >= self.confidence:
                    context['last_search_success'] = True
                    if self.click_after_search in ["left", "right"]:
                        h, w = template.shape[:2]
                        center_x = max_loc[0] + w // 2
                        center_y = max_loc[1] + h // 2
                        win32_mouse_move(center_x, center_y)
                        time.sleep(0.05)
                        win32_click(self.click_after_search)
                    break

class ActionCondition(Action):
    def __init__(self, step_data):
        self.condition_action = None
        cond_data = step_data.get("condition_action")
        if cond_data:
            self.condition_action = build_actions([cond_data])[0]
        self.if_cond = step_data.get("if", "last_search_success")
        self.then_steps = build_actions(step_data.get("then", []))
        
    def execute(self, context, flow_state):
        if not flow_state['running']: return
        
        if self.condition_action:
            self.condition_action.execute(context, flow_state)
            
        if context.get(self.if_cond, False):
            for action in self.then_steps:
                if not flow_state['running']: break
                action.execute(context, flow_state)

class ActionLoop(Action):
    def __init__(self, step_data):
        self.count = step_data.get("count", -1) # -1 为无限
        self.break_on_success = step_data.get("break_on_success", True)
        self.condition_action = None
        cond_data = step_data.get("condition_action")
        if cond_data:
            self.condition_action = build_actions([cond_data])[0]
        self.children = build_actions(step_data.get("children", []))
        
    def execute(self, context, flow_state):
        if not flow_state['running']: return
        c = 0
        while self.count == -1 or c < self.count:
            if not flow_state['running']: break
            
            if self.condition_action:
                context['last_search_success'] = False
                self.condition_action.execute(context, flow_state)
                success = context.get('last_search_success', False)
                if self.break_on_success and success:
                    break
                elif not self.break_on_success and not success:
                    break
                    
            for action in self.children:
                if not flow_state['running']: break
                action.execute(context, flow_state)
            c += 1

def build_actions(steps):
    actions = []
    for step in steps:
        action_type = step.get("action")
        if action_type == "sleep":
            actions.append(ActionSleep(step))
        elif action_type == "mouse_move":
            actions.append(ActionMouseMove(step))
        elif action_type == "mouse_click":
            actions.append(ActionMouseClick(step))
        elif action_type == "key_press":
            actions.append(ActionKeyPress(step))
        elif action_type == "image_search":
            actions.append(ActionImageSearch(step))
        elif action_type == "condition":
            actions.append(ActionCondition(step))
        elif action_type == "loop":
            actions.append(ActionLoop(step))
    return actions

# ================= 并发调度管理器 =================
class FlowManager:
    def __init__(self):
        self.flows = {} # id -> data
        self.flow_states = {} # id -> {'running': bool, 'thread': Thread}
        self.load_all_flows()

    def load_all_flows(self):
        self.flows.clear()
        if not os.path.exists(FLOWS_DIR):
            return
        for filename in os.listdir(FLOWS_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(FLOWS_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if "id" in data:
                            self.flows[data["id"]] = data
                except Exception as e:
                    print(f"Error loading flow {filename}: {e}")

    def save_flow(self, flow_data):
        if "id" not in flow_data:
            flow_data["id"] = f"flow_{int(time.time()*1000)}"
        flow_id = flow_data["id"]
        filepath = os.path.join(FLOWS_DIR, f"{flow_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(flow_data, f, indent=4, ensure_ascii=False)
        self.flows[flow_id] = flow_data
        return flow_id

    def delete_flow(self, flow_id):
        self.stop_flow(flow_id)
        if flow_id in self.flows:
            del self.flows[flow_id]
        filepath = os.path.join(FLOWS_DIR, f"{flow_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)

    def get_all_flows(self):
        # 加上运行状态
        res = []
        for fid, data in self.flows.items():
            run_state = self.flow_states.get(fid, {}).get("running", False)
            data["enabled"] = run_state
            res.append(data)
        return res

    def start_flow(self, flow_id):
        if flow_id not in self.flows: return
        self.stop_flow(flow_id) # 停止已有的
        
        flow_data = self.flows[flow_id]
        actions = build_actions(flow_data.get("steps", []))
        
        state = {'running': True}
        self.flow_states[flow_id] = state
        
        def flow_worker():
            context = {}
            for action in actions:
                if not state['running']: break
                try:
                    action.execute(context, state)
                except Exception as e:
                    print(f"Flow {flow_id} error: {e}")
                    break
            state['running'] = False

        t = threading.Thread(target=flow_worker, daemon=True)
        state['thread'] = t
        t.start()

    def stop_flow(self, flow_id):
        if flow_id in self.flow_states:
            self.flow_states[flow_id]['running'] = False
            # 等待线程自动退出
            self.flow_states.pop(flow_id)

    def stop_all(self):
        for fid in list(self.flow_states.keys()):
            self.stop_flow(fid)

flow_manager = FlowManager()
