import ctypes
import math
import sys

import pygetwindow as gw
from pynput import keyboard
from PySide6.QtCore import QObject, QPoint, Qt, Signal, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication

import RECT
from ui import LiquidOverlayWidget, TargetPreviewWidget


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", RECT.RECT),
        ("rcWork", RECT.RECT),
        ("dwFlags", ctypes.c_ulong),
    ]


class HotkeyBridge(QObject):
    alt_pressed = Signal()
    alt_released = Signal()


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def get_work_area(mouse_pos):
    monitor_default_to_nearest = 2
    point = POINT(mouse_pos.x(), mouse_pos.y())
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


def calculate_action(rel_x, rel_y, center_x, work_area):
    distance_sq = rel_x**2 + rel_y**2
    distance = math.sqrt(distance_sq)

    center_dead_zone = 14
    center_float_radius = 26
    maximize_radius = 48
    split_outer_near = 95
    split_outer_far = 145

    if distance <= center_dead_zone:
        return "none"

    if distance <= center_float_radius:
        return "center_float"

    if distance <= maximize_radius:
        return "maximize"

    angle = math.degrees(math.atan2(-rel_y, rel_x)) % 360

    if 22.5 <= angle < 67.5:
        base_action = "top_right"
    elif 67.5 <= angle < 112.5:
        base_action = "top_half"
    elif 112.5 <= angle < 157.5:
        base_action = "top_left"
    elif 157.5 <= angle < 202.5:
        base_action = "left_half"
    elif 202.5 <= angle < 247.5:
        base_action = "bottom_left"
    elif 247.5 <= angle < 292.5:
        base_action = "bottom_half"
    elif 292.5 <= angle < 337.5:
        base_action = "bottom_right"
    else:
        base_action = "right_half"

    if base_action == "left_half":
        work_left, _, work_right, _ = work_area
        edge_distance = max(1.0, float(center_x - work_left))
        edge_progress = min(1.0, max(0.0, (-rel_x) / edge_distance))

        if edge_progress >= 0.78:
            return "left_one_third"
        if edge_progress >= 0.42:
            return "left_half"
        return "left_two_thirds"

    if base_action == "right_half":
        work_left, _, work_right, _ = work_area
        edge_distance = max(1.0, float(work_right - center_x))
        edge_progress = min(1.0, max(0.0, rel_x / edge_distance))

        if edge_progress >= 0.78:
            return "right_one_third"
        if edge_progress >= 0.42:
            return "right_half"
        return "right_two_thirds"

    if base_action in ("top_half", "bottom_half") and distance >= split_outer_near:
        return "center_one_third"

    return base_action


def get_action_rect(action, work_area):
    left, top, right, bottom = work_area
    width = right - left
    height = bottom - top
    half_width = width // 2
    half_height = height // 2

    if action == "right_half":
        return left + half_width, top, half_width, height
    if action == "right_one_third":
        width_one_third = max(1, width // 3)
        return right - width_one_third, top, width_one_third, height
    if action == "right_two_thirds":
        width_two_thirds = max(1, (width * 2) // 3)
        return right - width_two_thirds, top, width_two_thirds, height
    if action == "top_right":
        return left + half_width, top, half_width, half_height
    if action == "top_half":
        return left, top, width, half_height
    if action == "center_one_third":
        width_one_third = max(1, width // 3)
        x = left + (width - width_one_third) // 2
        return x, top, width_one_third, height
    if action == "top_left":
        return left, top, half_width, half_height
    if action == "left_half":
        return left, top, half_width, height
    if action == "left_one_third":
        width_one_third = max(1, width // 3)
        return left, top, width_one_third, height
    if action == "left_two_thirds":
        width_two_thirds = max(1, (width * 2) // 3)
        return left, top, width_two_thirds, height
    if action == "bottom_left":
        return left, top + half_height, half_width, half_height
    if action == "bottom_half":
        return left, top + half_height, width, half_height
    if action == "bottom_right":
        return left + half_width, top + half_height, half_width, half_height
    if action == "maximize":
        return left, top, width, height
    if action == "center_float":
        float_width = max(1, int(width * 0.70))
        float_height = max(1, int(height * 0.78))
        x = left + (width - float_width) // 2
        y = top + (height - float_height) // 2
        return x, y, float_width, float_height
    return None


def apply_window_action(window, action, work_area):
    if action == "none":
        return

    if action == "maximize":
        window.maximize()
        return

    rect = get_action_rect(action, work_area)
    if rect is None:
        return

    x, y, width, height = rect
    window.restore()
    window.resizeTo(width, height)
    window.moveTo(x, y)


def safe_window_title(window):
    if window is None:
        return ""
    try:
        return window.title or ""
    except Exception:
        return ""


def run():
    labels = {
        "top_right": "右上角",
        "top_half": "上半屏",
        "top_left": "左上角",
        "left_half": "左半屏",
        "left_one_third": "左 1/3",
        "left_two_thirds": "左 2/3",
        "center_one_third": "中 1/3",
        "bottom_left": "左下角",
        "bottom_half": "下半屏",
        "bottom_right": "右下角",
        "right_half": "右半屏",
        "right_one_third": "右 1/3",
        "right_two_thirds": "右 2/3",
        "maximize": "最大化",
        "center_float": "居中浮窗",
        "none": "无变换",
    }
    icons = {
        "top_right": "↗",
        "top_half": "↑",
        "top_left": "↖",
        "left_half": "←",
        "left_one_third": "←",
        "left_two_thirds": "←",
        "center_one_third": "↕",
        "bottom_left": "↙",
        "bottom_half": "↓",
        "bottom_right": "↘",
        "right_half": "→",
        "right_one_third": "→",
        "right_two_thirds": "→",
        "maximize": "□",
        "center_float": "◉",
        "none": "•",
    }

    app = QApplication(sys.argv)
    bridge = HotkeyBridge()
    overlay = LiquidOverlayWidget(labels, icons)
    preview = TargetPreviewWidget()

    state = {
        "alt_pressed": False,
        "active_window": None,
        "work_area": (0, 0, 192, 108),
    }

    def mouse_pos():
        return QCursor.pos()

    def get_refresh_rate_for_cursor():
        screen = app.screenAt(mouse_pos())
        if screen is None:
            screen = app.primaryScreen()
        if screen is None:
            return 120.0
        refresh_rate = screen.refreshRate()
        if refresh_rate is None or refresh_rate <= 0:
            return 120.0
        return float(refresh_rate)

    def get_frame_interval_ms(refresh_rate):
        clamped_hz = max(60.0, min(165.0, refresh_rate))
        return max(4, int(round(1000.0 / clamped_hz)))

    def rel_from_overlay_center():
        pos = mouse_pos()
        center = overlay.center_point()
        return pos.x() - center.x(), pos.y() - center.y()

    def update_preview(action, show_target=True):
        overlay.set_action(action)

        if not show_target or action == "none":
            preview.hide_preview()
            return

        rect = get_action_rect(action, state["work_area"])
        if rect is None:
            preview.hide_preview()
            return

        x, y, width, height = rect
        preview.show_preview(x, y, width, height, overlay.accent_color())

    def on_update_tick():
        if not state["alt_pressed"]:
            return
        rel_x, rel_y = rel_from_overlay_center()
        center = overlay.center_point()
        action = calculate_action(rel_x, rel_y, center.x(), state["work_area"])
        update_preview(action, show_target=True)

    update_timer = QTimer()
    update_timer.setTimerType(Qt.TimerType.PreciseTimer)
    update_timer.setInterval(get_frame_interval_ms(120.0))
    update_timer.timeout.connect(on_update_tick)

    def handle_alt_press():
        if state["alt_pressed"]:
            return

        state["active_window"] = gw.getActiveWindow()
        state["work_area"] = get_work_area(mouse_pos())

        refresh_rate = get_refresh_rate_for_cursor()
        frame_interval_ms = get_frame_interval_ms(refresh_rate)
        update_timer.setInterval(frame_interval_ms)
        overlay.set_refresh_rate(refresh_rate)
        preview.set_refresh_rate(refresh_rate)

        overlay.center_at(mouse_pos())
        state["alt_pressed"] = True
        update_preview("none", show_target=True)
        overlay.show_animated()
        update_timer.start()

    def handle_alt_release():
        if not state["alt_pressed"]:
            return

        update_timer.stop()
        rel_x, rel_y = rel_from_overlay_center()
        center = overlay.center_point()
        action = calculate_action(rel_x, rel_y, center.x(), state["work_area"])
        update_preview(action, show_target=False)

        active_window = state["active_window"]
        if safe_window_title(active_window) != "Ring" and active_window is not None:
            apply_window_action(active_window, action, state["work_area"])

        preview.hide_preview()
        overlay.hide_animated()
        state["alt_pressed"] = False

    bridge.alt_pressed.connect(handle_alt_press)
    bridge.alt_released.connect(handle_alt_release)

    key_state = {"alt_down": False}

    def on_press(key):
        if key == keyboard.Key.alt_l and not key_state["alt_down"]:
            key_state["alt_down"] = True
            bridge.alt_pressed.emit()

    def on_release(key):
        if key == keyboard.Key.alt_l and key_state["alt_down"]:
            key_state["alt_down"] = False
            bridge.alt_released.emit()

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    exit_code = app.exec()
    listener.stop()
    sys.exit(exit_code)


if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, __file__, None, 1
    )
else:
    run()
