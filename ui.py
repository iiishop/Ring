import math

from PySide6.QtCore import QPoint, QRect, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(a, b, t):
    return QColor(
        int(lerp(a.red(), b.red(), t)),
        int(lerp(a.green(), b.green(), t)),
        int(lerp(a.blue(), b.blue(), t)),
        int(lerp(a.alpha(), b.alpha(), t)),
    )


def shortest_angle_lerp(a, b, t):
    diff = (b - a + math.pi) % (2 * math.pi) - math.pi
    return a + diff * t


class LiquidOverlayWidget(QWidget):
    def __init__(self, labels, icons):
        super().__init__()
        self.labels = labels
        self.icons = icons

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(188, 188)

        self._panel_alpha = 0.0
        self._target_alpha = 0.0
        self._fade_step = 0.0
        self._fade_steps_left = 0
        self._pulse_phase = 0.0
        self._frame_interval_ms = 16
        self._transition_duration_ms = 85
        self._transition_elapsed_ms = self._transition_duration_ms

        self._action = "none"
        self._color_map = {
            "top_right": QColor("#93c5fd"),
            "top_half": QColor("#7dd3fc"),
            "top_left": QColor("#c4b5fd"),
            "left_half": QColor("#d8b4fe"),
            "left_one_third": QColor("#c4b5fd"),
            "left_two_thirds": QColor("#a78bfa"),
            "center_one_third": QColor("#93c5fd"),
            "bottom_left": QColor("#f9a8d4"),
            "bottom_half": QColor("#fda4af"),
            "bottom_right": QColor("#fdba74"),
            "right_half": QColor("#86efac"),
            "right_one_third": QColor("#86efac"),
            "right_two_thirds": QColor("#4ade80"),
            "maximize": QColor("#67e8f9"),
            "center_float": QColor("#e2e8f0"),
            "none": QColor("#94a3b8"),
        }
        self._accent = QColor(self._color_map["none"])
        self._accent_from = QColor(self._accent)
        self._accent_to = QColor(self._accent)

        self._angle_map = {
            "top_half": -math.pi / 2,
            "top_right": -math.pi / 4,
            "right_half": 0,
            "right_one_third": 0,
            "right_two_thirds": 0,
            "center_one_third": -math.pi / 2,
            "bottom_right": math.pi / 4,
            "bottom_half": math.pi / 2,
            "bottom_left": 3 * math.pi / 4,
            "left_half": math.pi,
            "left_one_third": math.pi,
            "left_two_thirds": math.pi,
            "top_left": -3 * math.pi / 4,
        }
        self._angle = -math.pi / 2
        self._angle_from = self._angle
        self._angle_to = self._angle

        self._transition_t = 1.0
        self._transition_timer = QTimer(self)
        self._transition_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._transition_timer.timeout.connect(self._on_transition_tick)

        self._fade_timer = QTimer(self)
        self._fade_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._fade_timer.timeout.connect(self._on_fade_tick)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._pulse_timer.timeout.connect(self._on_pulse_tick)

        self.hide()

    def center_at(self, mouse_pos):
        self.move(mouse_pos.x() - self.width() // 2, mouse_pos.y() - self.height() // 2)

    def center_point(self):
        return QPoint(self.x() + self.width() // 2, self.y() + self.height() // 2)

    def set_action(self, action):
        if action == self._action:
            return

        self._action = action
        self._accent_from = QColor(self._accent)
        self._accent_to = QColor(self._color_map.get(action, self._color_map["none"]))

        self._angle_from = self._angle
        self._angle_to = self._angle_map.get(action, self._angle)

        self._transition_t = 0.0
        self._transition_elapsed_ms = 0
        self._transition_timer.start(self._frame_interval_ms)

    def set_refresh_rate(self, hz):
        clamped_hz = max(60.0, min(240.0, float(hz)))
        self._frame_interval_ms = max(4, int(round(1000.0 / clamped_hz)))

    def accent_color(self):
        return QColor(self._accent)

    def show_animated(self):
        self._pulse_timer.start(self._frame_interval_ms)
        self._start_fade(1.0)

    def hide_animated(self):
        self._start_fade(0.0)

    def _start_fade(self, target_alpha):
        self._target_alpha = target_alpha
        duration_ms = 90
        steps = max(6, int(round(duration_ms / self._frame_interval_ms)))
        self._fade_steps_left = steps
        self._fade_step = (target_alpha - self._panel_alpha) / steps
        if target_alpha > 0:
            self.show()
        self._fade_timer.start(self._frame_interval_ms)

    def _on_fade_tick(self):
        if self._fade_steps_left <= 0:
            self._panel_alpha = self._target_alpha
            self._fade_timer.stop()
            if self._panel_alpha <= 0:
                self._pulse_timer.stop()
                self.hide()
            self.update()
            return

        self._panel_alpha = max(0.0, min(1.0, self._panel_alpha + self._fade_step))
        self._fade_steps_left -= 1
        self.update()

    def _on_transition_tick(self):
        self._transition_elapsed_ms += self._frame_interval_ms
        linear_t = min(1.0, self._transition_elapsed_ms / self._transition_duration_ms)
        self._transition_t = linear_t * linear_t * (3.0 - 2.0 * linear_t)
        self._accent = lerp_color(
            self._accent_from, self._accent_to, self._transition_t
        )
        self._angle = shortest_angle_lerp(
            self._angle_from, self._angle_to, self._transition_t
        )
        self.update()
        if self._transition_t >= 1.0:
            self._transition_timer.stop()

    def _on_pulse_tick(self):
        self._pulse_phase += (self._frame_interval_ms / 1000.0) * 2.35
        self.update()

    def paintEvent(self, _event):
        if self._panel_alpha <= 0:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setOpacity(self._panel_alpha)

        center = QPoint(self.width() // 2, self.height() // 2)
        wave = math.sin(self._pulse_phase)
        micro = math.sin(self._pulse_phase * 0.5 + 1.1)
        pulse = (wave * 0.75 + micro * 0.25 + 1.0) * 0.5
        pulse = pulse * pulse * (3.0 - 2.0 * pulse)

        outer_r = 68 + pulse * 1.6
        main_r = 60 + pulse * 1.0
        inner_r = 50

        glow = QColor(self._accent)
        glow.setAlpha(int(52 + pulse * 32))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(glow, 10))
        p.drawEllipse(center, int(outer_r), int(outer_r))

        ring_color = QColor(236, 244, 255, 210)
        p.setPen(QPen(ring_color, 2))
        p.drawEllipse(center, int(main_r), int(main_r))

        core_color = QColor(205, 222, 242, 90)
        p.setPen(QPen(core_color, 1))
        p.drawEllipse(center, inner_r, inner_r)

        if self._action == "maximize":
            p.setPen(
                QPen(
                    QColor(
                        self._accent.red(),
                        self._accent.green(),
                        self._accent.blue(),
                        210,
                    ),
                    4,
                )
            )
            p.drawEllipse(center, int(main_r), int(main_r))
        elif self._action == "center_float":
            p.setPen(
                QPen(
                    QColor(
                        self._accent.red(),
                        self._accent.green(),
                        self._accent.blue(),
                        220,
                    ),
                    2,
                )
            )
            p.setBrush(
                QColor(
                    self._accent.red(), self._accent.green(), self._accent.blue(), 60
                )
            )
            p.drawEllipse(center, 11, 11)
        elif self._action == "center_one_third":
            p.setPen(
                QPen(
                    QColor(
                        self._accent.red(),
                        self._accent.green(),
                        self._accent.blue(),
                        220,
                    ),
                    3,
                )
            )
            p.setBrush(
                QColor(
                    self._accent.red(), self._accent.green(), self._accent.blue(), 48
                )
            )
            p.drawRoundedRect(QRect(center.x() - 10, center.y() - 36, 20, 72), 9, 9)
        elif self._action != "none":
            arc_rect = QRectF(
                center.x() - main_r,
                center.y() - main_r,
                main_r * 2,
                main_r * 2,
            )
            start_deg = int((-math.degrees(self._angle) - 18) * 16)
            span_deg = int(36 * 16)
            accent_pen = QPen(
                QColor(
                    self._accent.red(), self._accent.green(), self._accent.blue(), 230
                ),
                4,
            )
            p.setPen(accent_pen)
            p.drawArc(arc_rect, start_deg, span_deg)

            dot_x = center.x() + math.cos(self._angle) * main_r
            dot_y = center.y() + math.sin(self._angle) * main_r
            p.setPen(Qt.PenStyle.NoPen)
            dot_color = QColor(self._accent)
            dot_color.setAlpha(230)
            p.setBrush(dot_color)
            p.drawEllipse(QPoint(int(dot_x), int(dot_y)), 4, 4)


class TargetPreviewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._color = QColor("#7dd3fc")
        self._target_color = QColor(self._color)
        self._opacity = 0.0
        self._target_opacity = 0.0
        self._frame_interval_ms = 16

        self._current_rect = QRectF(0, 0, 0, 0)
        self._from_rect = QRectF(0, 0, 0, 0)
        self._to_rect = QRectF(0, 0, 0, 0)
        self._target_rect = QRectF(0, 0, 0, 0)
        self._rect_t = 1.0
        self._rect_duration_ms = 90
        self._rect_elapsed_ms = self._rect_duration_ms
        self._is_morphing = False

        self._anim_timer = QTimer(self)
        self._anim_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._anim_timer.timeout.connect(self._on_anim_tick)

        self.hide()

    def set_refresh_rate(self, hz):
        clamped_hz = max(60.0, min(240.0, float(hz)))
        self._frame_interval_ms = max(4, int(round(1000.0 / clamped_hz)))

    @staticmethod
    def _rect_almost_equal(a, b, eps=0.6):
        return (
            abs(a.x() - b.x()) <= eps
            and abs(a.y() - b.y()) <= eps
            and abs(a.width() - b.width()) <= eps
            and abs(a.height() - b.height()) <= eps
        )

    def show_preview(self, x, y, width, height, color):
        if width <= 0 or height <= 0:
            self.hide_preview()
            return

        next_color = QColor(color)
        target_rect = QRectF(float(x), float(y), float(width), float(height))

        if not self.isVisible():
            self._color = QColor(next_color)
            self._target_color = QColor(next_color)
            self._current_rect = QRectF(target_rect)
            self._target_rect = QRectF(target_rect)
            self._apply_rect(self._current_rect)
            self._start_fade(1.0)
            return

        rect_changed = not self._rect_almost_equal(target_rect, self._target_rect)
        color_changed = next_color != self._target_color

        if rect_changed:
            self._target_rect = QRectF(target_rect)
            self._from_rect = QRectF(self._current_rect)
            self._to_rect = QRectF(target_rect)
            self._rect_t = 0.0
            self._rect_elapsed_ms = 0
            self._is_morphing = True

        if color_changed:
            self._target_color = QColor(next_color)

        self._start_fade(1.0)

    def hide_preview(self):
        if not self.isVisible() and self._opacity <= 0:
            return
        self._start_fade(0.0)

    def _start_fade(self, target_opacity):
        self._target_opacity = target_opacity
        if target_opacity > 0:
            self.show()
            self.raise_()
        if not self._anim_timer.isActive():
            self._anim_timer.start(self._frame_interval_ms)

    def _on_anim_tick(self):
        dt = self._frame_interval_ms / 1000.0

        alpha_tau = 0.04
        alpha_blend = 1.0 - math.exp(-dt / alpha_tau)
        self._opacity = (
            self._opacity + (self._target_opacity - self._opacity) * alpha_blend
        )

        color_tau = 0.06
        color_blend = 1.0 - math.exp(-dt / color_tau)
        self._color = lerp_color(self._color, self._target_color, color_blend)

        if self._is_morphing:
            self._rect_elapsed_ms += self._frame_interval_ms
            linear_t = min(1.0, self._rect_elapsed_ms / self._rect_duration_ms)
            eased_t = linear_t * linear_t * (3.0 - 2.0 * linear_t)
            self._current_rect = QRectF(
                lerp(self._from_rect.x(), self._to_rect.x(), eased_t),
                lerp(self._from_rect.y(), self._to_rect.y(), eased_t),
                lerp(self._from_rect.width(), self._to_rect.width(), eased_t),
                lerp(self._from_rect.height(), self._to_rect.height(), eased_t),
            )
            self._apply_rect(self._current_rect)
            if linear_t >= 1.0:
                self._is_morphing = False

        if (
            self._opacity <= 0.01
            and self._target_opacity <= 0
            and not self._is_morphing
        ):
            self._opacity = 0.0
            self.hide()
            self._anim_timer.stop()
            self.update()
            return

        self.update()

    def _apply_rect(self, rectf):
        self.setGeometry(
            int(rectf.x()),
            int(rectf.y()),
            max(1, int(rectf.width())),
            max(1, int(rectf.height())),
        )
        self.update()

    def paintEvent(self, _event):
        if self._opacity <= 0:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setOpacity(self._opacity)

        fill = QColor(self._color)
        fill.setAlpha(40)
        border = QColor(self._color)
        border.setAlpha(185)

        r = self.rect().adjusted(2, 2, -2, -2)
        p.setBrush(fill)
        p.setPen(QPen(border, 2))
        p.drawRoundedRect(QRect(r), 14, 14)
