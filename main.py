import math
import tkinter as tk
from pynput import keyboard
import pygetwindow as gw
import ctypes
import sys
import RECT
from ui import RingOverlayUI


alt_pressed = False
active_window = None
current_work_area = (0, 0, 192, 108)


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", RECT.RECT),
        ("rcWork", RECT.RECT),
        ("dwFlags", ctypes.c_ulong),
    ]


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run():
    labels = {
        "top_right": "右上角",
        "top_half": "上半屏",
        "top_left": "左上角",
        "left_half": "左半屏",
        "bottom_left": "左下角",
        "bottom_half": "下半屏",
        "bottom_right": "右下角",
        "right_half": "右半屏",
        "maximize": "最大化",
        "none": "无变换",
    }
    icons = {
        "top_right": "↗",
        "top_half": "↑",
        "top_left": "↖",
        "left_half": "←",
        "bottom_left": "↙",
        "bottom_half": "↓",
        "bottom_right": "↘",
        "right_half": "→",
        "maximize": "□",
        "none": "•",
    }

    ui_job = None

    def get_mouse_position():
        x = root.winfo_pointerx()
        y = root.winfo_pointery()
        return x, y

    def get_rel():
        x, y = get_mouse_position()
        return ui.get_rel(x, y)

    def get_work_area():
        monitor_default_to_nearest = 2
        mouse_x, mouse_y = get_mouse_position()
        point = POINT(mouse_x, mouse_y)
        monitor_handle = ctypes.windll.user32.MonitorFromPoint(
            point, monitor_default_to_nearest
        )

        if monitor_handle:
            monitor_info = MONITORINFO()
            monitor_info.cbSize = ctypes.sizeof(MONITORINFO)
            if ctypes.windll.user32.GetMonitorInfoW(
                monitor_handle, ctypes.byref(monitor_info)
            ):
                rc_work = monitor_info.rcWork
                return rc_work.left, rc_work.top, rc_work.right, rc_work.bottom

        rect = RECT.RECT()
        ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)
        return rect.left, rect.top, rect.right, rect.bottom

    def calculate_action(rel_x, rel_y):
        distance_sq = rel_x**2 + rel_y**2

        if 30**2 < distance_sq < 50**2:
            return "maximize"

        if distance_sq <= 50**2:
            return "none"

        angle = math.degrees(math.atan2(-rel_y, rel_x)) % 360

        if 22.5 <= angle < 67.5:
            return "top_right"
        if 67.5 <= angle < 112.5:
            return "top_half"
        if 112.5 <= angle < 157.5:
            return "top_left"
        if 157.5 <= angle < 202.5:
            return "left_half"
        if 202.5 <= angle < 247.5:
            return "bottom_left"
        if 247.5 <= angle < 292.5:
            return "bottom_half"
        if 292.5 <= angle < 337.5:
            return "bottom_right"
        return "right_half"

    def apply_window_action(window, action, work_area):
        left, top, right, bottom = work_area
        width = right - left
        height = bottom - top
        half_width = width // 2
        half_height = height // 2

        if action == "none":
            return
        if action == "maximize":
            window.maximize()
            return

        window.restore()
        if action == "right_half":
            window.resizeTo(half_width, height)
            window.moveTo(left + half_width, top)
        elif action == "top_right":
            window.resizeTo(half_width, half_height)
            window.moveTo(left + half_width, top)
        elif action == "top_half":
            window.resizeTo(width, half_height)
            window.moveTo(left, top)
        elif action == "top_left":
            window.resizeTo(half_width, half_height)
            window.moveTo(left, top)
        elif action == "left_half":
            window.resizeTo(half_width, height)
            window.moveTo(left, top)
        elif action == "bottom_left":
            window.resizeTo(half_width, half_height)
            window.moveTo(left, top + half_height)
        elif action == "bottom_half":
            window.resizeTo(width, half_height)
            window.moveTo(left, top + half_height)
        elif action == "bottom_right":
            window.resizeTo(half_width, half_height)
            window.moveTo(left + half_width, top + half_height)

    def get_action_rect(action, work_area):
        left, top, right, bottom = work_area
        width = right - left
        height = bottom - top
        half_width = width // 2
        half_height = height // 2

        if action == "right_half":
            return left + half_width, top, half_width, height
        if action == "top_right":
            return left + half_width, top, half_width, half_height
        if action == "top_half":
            return left, top, width, half_height
        if action == "top_left":
            return left, top, half_width, half_height
        if action == "left_half":
            return left, top, half_width, height
        if action == "bottom_left":
            return left, top + half_height, half_width, half_height
        if action == "bottom_half":
            return left, top + half_height, width, half_height
        if action == "bottom_right":
            return left + half_width, top + half_height, half_width, half_height
        if action == "maximize":
            return left, top, width, height
        return None

    def safe_window_title(window):
        if window is None:
            return ""
        try:
            return window.title or ""
        except Exception:
            return ""

    def set_preview(action, show_target=True):
        ui.set_preview(action, current_work_area, get_action_rect, show_target)

    def update_label_loop():
        nonlocal ui_job
        if not alt_pressed:
            ui_job = None
            return
        rel_x, rel_y = get_rel()
        action = calculate_action(rel_x, rel_y)
        set_preview(action)
        ui_job = root.after(33, update_label_loop)

    def start_label_loop():
        nonlocal ui_job
        if ui_job is None:
            update_label_loop()

    def stop_label_loop():
        nonlocal ui_job
        if ui_job is not None:
            root.after_cancel(ui_job)
            ui_job = None

    def handle_alt_press():
        global alt_pressed, active_window, current_work_area
        if alt_pressed:
            return

        print("按下Alt键")
        active_window = gw.getActiveWindow()
        print(safe_window_title(active_window))
        current_work_area = get_work_area()

        mouse_x, mouse_y = get_mouse_position()
        ui.center_at(mouse_x, mouse_y)
        alt_pressed = True
        set_preview("none")
        start_label_loop()
        ui.show_panel()

    def handle_alt_release():
        global alt_pressed
        if not alt_pressed:
            return

        print("释放Alt键")
        stop_label_loop()
        ui.hide_target_preview()

        rel_x, rel_y = get_rel()
        action = calculate_action(rel_x, rel_y)
        set_preview(action, show_target=False)

        if safe_window_title(active_window) != "Ring" and active_window is not None:
            print(labels[action])
            apply_window_action(active_window, action, current_work_area)

        ui.hide_panel()
        alt_pressed = False

    def on_alt_press(key):
        if key == keyboard.Key.alt_l:
            root.after(0, handle_alt_press)

    def on_alt_release(key):
        if key == keyboard.Key.alt_l:
            root.after(0, handle_alt_release)

    root = tk.Tk()
    root.title("Ring")
    root.attributes("-alpha", 0)  # 设置透明度
    root.geometry("1x1+0+0")

    ui = RingOverlayUI(root, labels, icons)

    listener = keyboard.Listener(on_press=on_alt_press, on_release=on_alt_release)
    listener.start()

    root.mainloop()


if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, __file__, None, 1
    )
else:
    run()
