import math
import tkinter as tk
from pynput import keyboard
import pygetwindow as gw
import ctypes
import sys
import RECT


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
    fade_job = None
    current_alpha = 0.0

    def get_mouse_position():
        x = root.winfo_pointerx()
        y = root.winfo_pointery()
        return x, y

    def get_rel():
        x, y = get_mouse_position()
        sub_center_x = sub_window.winfo_x() + sub_window.winfo_width() // 2
        sub_center_y = sub_window.winfo_y() + sub_window.winfo_height() // 2
        rel_x = x - sub_center_x
        rel_y = y - sub_center_y
        return rel_x, rel_y

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

    def update_target_preview(action):
        if action == "none":
            target_preview.withdraw()
            return

        rect = get_action_rect(action, current_work_area)
        if rect is None:
            target_preview.withdraw()
            return

        x, y, width, height = rect
        if width <= 0 or height <= 0:
            target_preview.withdraw()
            return

        target_preview.geometry(f"{width}x{height}+{x}+{y}")
        target_preview.deiconify()
        target_preview.lift()
        sub_window.lift()

    def safe_window_title(window):
        if window is None:
            return ""
        try:
            return window.title or ""
        except Exception:
            return ""

    def set_preview(action, rel_x, rel_y):
        icon_var.set(icons[action])
        action_var.set(labels[action])
        detail_var.set(f"相对位置: ({rel_x}, {rel_y})")
        update_target_preview(action)

        if action == "none":
            action_label.configure(fg="#9aa7bd")
        elif action == "maximize":
            action_label.configure(fg="#6fd0ff")
        else:
            action_label.configure(fg="#8cf2a5")

    def update_label_loop():
        nonlocal ui_job
        if not alt_pressed:
            ui_job = None
            return
        rel_x, rel_y = get_rel()
        action = calculate_action(rel_x, rel_y)
        set_preview(action, rel_x, rel_y)
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

    def animate_alpha(target_alpha, duration_ms=120, step_ms=10):
        nonlocal fade_job, current_alpha

        if fade_job is not None:
            root.after_cancel(fade_job)
            fade_job = None

        start_alpha = current_alpha
        steps = max(1, duration_ms // step_ms)
        delta = (target_alpha - start_alpha) / steps

        if target_alpha > 0:
            sub_window.deiconify()

        def step(index):
            nonlocal fade_job, current_alpha
            alpha = start_alpha + delta * index
            alpha = max(0.0, min(1.0, alpha))
            current_alpha = alpha
            sub_window.attributes("-alpha", alpha)

            if index < steps:
                fade_job = root.after(step_ms, lambda: step(index + 1))
            else:
                fade_job = None
                current_alpha = target_alpha
                sub_window.attributes("-alpha", target_alpha)
                if target_alpha <= 0:
                    sub_window.withdraw()

        step(1)

    def center_sub_window_at_mouse():
        x, y = get_mouse_position()
        root.update_idletasks()
        window_width = sub_window.winfo_width()
        window_height = sub_window.winfo_height()
        sub_window.geometry(f"+{x - window_width // 2}+{y - window_height // 2}")

    def handle_alt_press():
        global alt_pressed, active_window, current_work_area
        if alt_pressed:
            return

        print("按下Alt键")
        active_window = gw.getActiveWindow()
        print(safe_window_title(active_window))
        current_work_area = get_work_area()

        center_sub_window_at_mouse()
        alt_pressed = True
        set_preview("none", 0, 0)
        start_label_loop()
        animate_alpha(1.0)

    def handle_alt_release():
        global alt_pressed
        if not alt_pressed:
            return

        print("释放Alt键")
        stop_label_loop()
        target_preview.withdraw()

        rel_x, rel_y = get_rel()
        action = calculate_action(rel_x, rel_y)
        set_preview(action, rel_x, rel_y)

        if safe_window_title(active_window) != "Ring" and active_window is not None:
            print(labels[action])
            apply_window_action(active_window, action, current_work_area)

        animate_alpha(0.0)
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

    action_var = tk.StringVar(value=labels["none"])
    detail_var = tk.StringVar(value="相对位置: (0, 0)")
    icon_var = tk.StringVar(value=icons["none"])

    sub_window = tk.Toplevel(root)
    sub_window.attributes("-alpha", 0)
    sub_window.overrideredirect(True)
    sub_window.attributes("-topmost", 1)
    sub_window.configure(bg="#0e141f")
    sub_window.withdraw()

    card = tk.Frame(
        sub_window,
        bg="#172233",
        bd=0,
        highlightthickness=1,
        highlightbackground="#2c425f",
        padx=16,
        pady=12,
    )
    card.pack(padx=2, pady=2)

    title_label = tk.Label(
        card,
        text="Ring Snap",
        fg="#9ec7ff",
        bg="#172233",
        font=("Segoe UI Semibold", 10),
    )
    title_label.pack(anchor="w")

    icon_label = tk.Label(
        card,
        textvariable=icon_var,
        fg="#8cf2a5",
        bg="#172233",
        font=("Segoe UI Symbol", 26),
    )
    icon_label.pack(anchor="center", pady=(4, 0))

    action_label = tk.Label(
        card,
        textvariable=action_var,
        fg="#9aa7bd",
        bg="#172233",
        font=("Segoe UI Semibold", 13),
    )
    action_label.pack(anchor="center")

    detail_label = tk.Label(
        card,
        textvariable=detail_var,
        fg="#93a0b5",
        bg="#172233",
        font=("Consolas", 9),
    )
    detail_label.pack(anchor="center", pady=(4, 0))

    target_preview = tk.Toplevel(root)
    target_preview.overrideredirect(True)
    target_preview.attributes("-topmost", 1)
    target_preview.attributes("-alpha", 0.18)
    target_preview.configure(bg="#6fd0ff")
    target_preview.withdraw()

    listener = keyboard.Listener(on_press=on_alt_press, on_release=on_alt_release)
    listener.start()

    root.mainloop()


if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, __file__, None, 1
    )
else:
    run()
