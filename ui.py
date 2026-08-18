import math

from PySide6.QtCore import QElapsedTimer, QPoint, QRect, QRectF, QTimer, Qt
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


def shortest_angle_delta(current, target):
    return (target - current + math.pi) % (2 * math.pi) - math.pi


def fbm_noise(t, phases):
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    norm = 0.0
    for phase in phases:
        value += amplitude * math.sin(t * frequency + phase)
        norm += amplitude
        frequency *= 2.03
        amplitude *= 0.5
    if norm <= 0:
        return 0.0
    return value / norm


def spring_update(current, target, velocity, stiffness, damping, dt):
    force = -stiffness * (current - target)
    velocity += force * dt
    velocity *= math.exp(-damping * dt)
    current += velocity * dt
    return current, velocity


def spring_done(current, target, velocity, pos_eps=0.01, vel_eps=0.01):
    return abs(current - target) <= pos_eps and abs(velocity) <= vel_eps


SPRING_STIFFNESS = 200.0
SPRING_DAMPING = 26.0


def clamp_refresh_rate(hz):
    """Clamp refresh rate to the allowed range [60, 240] Hz."""
    return max(60.0, min(240.0, float(hz)))


def compute_frame_interval_ms(hz):
    """Compute frame interval in ms from a clamped refresh rate."""
    return max(4, int(round(1000.0 / hz)))


def compute_dt(elapsed, frame_interval_ms):
    """Compute delta-time in seconds from a QElapsedTimer.

    Clamps dt to (0.0, 0.05] and falls back to frame_interval_ms when the
    timer is invalid or dt would be <= 0.
    """
    elapsed_ms = elapsed.restart() if elapsed.isValid() else 0
    dt = max(0.0, min(0.05, elapsed_ms / 1000.0))
    if dt <= 0.0:
        dt = frame_interval_ms / 1000.0
    return dt


class LiquidOverlayWidget(QWidget):
    HYSTERESIS_FRAMES = 3

    def __init__(self, labels):
        super().__init__()
        self.labels = labels

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
        self._fade_from_alpha = 0.0
        self._fade_elapsed_s = 0.0
        self._fade_duration_s = 0.072
        self._is_fading = False
        self._pulse_phase = 0.0
        self._frame_interval_ms = 16

        self._action = "none"
        self._candidate_action = "none"
        self._candidate_frames = 0
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
        self._accent_rgba = [
            float(self._accent.red()),
            float(self._accent.green()),
            float(self._accent.blue()),
            float(self._accent.alpha()),
        ]
        self._accent_target_rgba = list(self._accent_rgba)
        self._accent_velocity = [0.0, 0.0, 0.0, 0.0]

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
        self._angle_target = self._angle
        self._angle_velocity = 0.0

        self._marker_rect = QRectF(0, 0, 0, 0)
        self._marker_rect_target = QRectF(0, 0, 0, 0)
        self._marker_rect_velocity = [0.0, 0.0, 0.0, 0.0]
        self._marker_visible = 0.0
        self._marker_visible_target = 0.0
        self._marker_visible_velocity = 0.0

        self._jitter_x = 0.0
        self._jitter_y = 0.0
        self._time_s = 0.0
        self._noise_phases_x = (0.19, 1.17, 2.91, 4.63)
        self._noise_phases_y = (0.83, 2.07, 3.71, 5.11)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._refresh_timer.timeout.connect(self._on_refresh_tick)
        self._elapsed = QElapsedTimer()

        self.hide()

    def _marker_target_rect(self, action):
        c = self.width() / 2.0
        if action == "none":
            return QRectF(c, c, 0, 0), 0.0
        if action == "center_float":
            return QRectF(c - 17, c - 17, 34, 34), 1.0
        if action == "center_one_third":
            return QRectF(c - 9, c - 34, 18, 68), 1.0
        if action == "maximize":
            return QRectF(c - 20, c - 20, 40, 40), 1.0

        marker_map = {
            "left_one_third": QRectF(c - 48, c - 34, 14, 68),
            "left_half": QRectF(c - 36, c - 32, 18, 64),
            "left_two_thirds": QRectF(c - 24, c - 30, 22, 60),
            "right_one_third": QRectF(c + 34, c - 34, 14, 68),
            "right_half": QRectF(c + 18, c - 32, 18, 64),
            "right_two_thirds": QRectF(c + 2, c - 30, 22, 60),
            "top_half": QRectF(c - 32, c - 36, 64, 18),
            "bottom_half": QRectF(c - 32, c + 18, 64, 18),
            "top_left": QRectF(c - 42, c - 42, 22, 22),
            "top_right": QRectF(c + 20, c - 42, 22, 22),
            "bottom_left": QRectF(c - 42, c + 20, 22, 22),
            "bottom_right": QRectF(c + 20, c + 20, 22, 22),
        }
        return marker_map.get(action, QRectF(c, c, 0, 0)), 1.0

    def center_at(self, mouse_pos):
        self.move(mouse_pos.x() - self.width() // 2, mouse_pos.y() - self.height() // 2)

    def center_point(self):
        return QPoint(self.x() + self.width() // 2, self.y() + self.height() // 2)

    def set_action(self, action):
        if action == self._action:
            return

        self._action = action
        self._candidate_action = action
        self._candidate_frames = self.HYSTERESIS_FRAMES
        accent = self._color_map.get(action, self._color_map["none"])
        self._accent_target_rgba = [
            float(accent.red()),
            float(accent.green()),
            float(accent.blue()),
            float(accent.alpha()),
        ]
        self._angle_target = self._angle_map.get(action, self._angle)
        self._marker_rect_target, self._marker_visible_target = self._marker_target_rect(
            action
        )
        self._ensure_refresh_running()

    def set_action_stable(self, action):
        if action == self._candidate_action:
            self._candidate_frames += 1
        else:
            self._candidate_action = action
            self._candidate_frames = 1

        if (
            self._candidate_frames >= self.HYSTERESIS_FRAMES
            and action != self._action
        ):
            self.set_action(action)

    def set_refresh_rate(self, hz):
        clamped_hz = clamp_refresh_rate(hz)
        self._frame_interval_ms = compute_frame_interval_ms(clamped_hz)
        if self._refresh_timer.isActive():
            self._refresh_timer.start(self._frame_interval_ms)

    def accent_color(self):
        return QColor(self._accent)

    def show_animated(self):
        if self._panel_alpha <= 0.0 and self._target_alpha <= 0.0 and self._action != "none":
            self.set_action("none")
        self._start_fade(1.0)

    def hide_animated(self):
        self._start_fade(0.0)

    def _start_fade(self, target_alpha):
        self._fade_from_alpha = self._panel_alpha
        self._target_alpha = target_alpha
        self._fade_elapsed_s = 0.0
        self._is_fading = True
        if target_alpha > 0:
            self.show()
        self._ensure_refresh_running()

    def _ensure_refresh_running(self):
        if self._refresh_timer.isActive():
            return
        self._elapsed.restart()
        self._refresh_timer.start(self._frame_interval_ms)

    def _update_springs(self, dt):
        active = False

        for index in range(4):
            current = self._accent_rgba[index]
            target = self._accent_target_rgba[index]
            velocity = self._accent_velocity[index]
            current, velocity = spring_update(
                current,
                target,
                velocity,
                SPRING_STIFFNESS,
                SPRING_DAMPING,
                dt,
            )
            if spring_done(current, target, velocity, pos_eps=0.35, vel_eps=1.0):
                current = target
                velocity = 0.0
            else:
                active = True
            self._accent_rgba[index] = current
            self._accent_velocity[index] = velocity

        self._accent = QColor(
            max(0, min(255, int(round(self._accent_rgba[0])))),
            max(0, min(255, int(round(self._accent_rgba[1])))),
            max(0, min(255, int(round(self._accent_rgba[2])))),
            max(0, min(255, int(round(self._accent_rgba[3])))),
        )

        angle_target = self._angle + shortest_angle_delta(self._angle, self._angle_target)
        self._angle, self._angle_velocity = spring_update(
            self._angle,
            angle_target,
            self._angle_velocity,
            SPRING_STIFFNESS,
            SPRING_DAMPING,
            dt,
        )
        if spring_done(
            self._angle,
            angle_target,
            self._angle_velocity,
            pos_eps=0.002,
            vel_eps=0.01,
        ):
            self._angle = angle_target
            self._angle_velocity = 0.0
        else:
            active = True
        self._angle = ((self._angle + math.pi) % (2 * math.pi)) - math.pi

        rect_values = [
            self._marker_rect.x(),
            self._marker_rect.y(),
            self._marker_rect.width(),
            self._marker_rect.height(),
        ]
        target_values = [
            self._marker_rect_target.x(),
            self._marker_rect_target.y(),
            self._marker_rect_target.width(),
            self._marker_rect_target.height(),
        ]
        next_values = []
        for index in range(4):
            current, velocity = spring_update(
                rect_values[index],
                target_values[index],
                self._marker_rect_velocity[index],
                SPRING_STIFFNESS,
                SPRING_DAMPING,
                dt,
            )
            if spring_done(current, target_values[index], velocity, pos_eps=0.2, vel_eps=0.5):
                current = target_values[index]
                velocity = 0.0
            else:
                active = True
            next_values.append(current)
            self._marker_rect_velocity[index] = velocity
        self._marker_rect = QRectF(*next_values)

        self._marker_visible, self._marker_visible_velocity = spring_update(
            self._marker_visible,
            self._marker_visible_target,
            self._marker_visible_velocity,
            SPRING_STIFFNESS,
            SPRING_DAMPING,
            dt,
        )
        if spring_done(
            self._marker_visible,
            self._marker_visible_target,
            self._marker_visible_velocity,
            pos_eps=0.01,
            vel_eps=0.02,
        ):
            self._marker_visible = self._marker_visible_target
            self._marker_visible_velocity = 0.0
        else:
            active = True

        return active

    def _on_refresh_tick(self):
        dt = compute_dt(self._elapsed, self._frame_interval_ms)

        needs_update = False

        if self._is_fading:
            self._fade_elapsed_s += dt
            t = min(1.0, self._fade_elapsed_s / self._fade_duration_s)
            self._panel_alpha = lerp(self._fade_from_alpha, self._target_alpha, t)
            if t >= 1.0:
                self._panel_alpha = self._target_alpha
                self._is_fading = False
            needs_update = True

        if self._panel_alpha > 0.0:
            self._pulse_phase += dt * 2.35
            self._time_s += dt

            jitter_amp = 0.72
            self._jitter_x = (
                fbm_noise(self._time_s * 0.85, self._noise_phases_x) * jitter_amp
            )
            self._jitter_y = (
                fbm_noise(self._time_s * 0.92 + 13.0, self._noise_phases_y) * jitter_amp
            )
            needs_update = True

        springs_active = self._update_springs(dt)
        needs_update = needs_update or springs_active

        if self._panel_alpha <= 0.0 and self._target_alpha <= 0.0 and not self._is_fading:
            self._panel_alpha = 0.0
            self.hide()
            if not springs_active:
                self._refresh_timer.stop()

        if needs_update:
            self.update()

    def paintEvent(self, _event):
        if self._panel_alpha <= 0:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setOpacity(self._panel_alpha)

        center_x = self.width() / 2.0 + self._jitter_x
        center_y = self.height() / 2.0 + self._jitter_y
        center = QPoint(int(center_x), int(center_y))
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

        if self._marker_visible > 0.01:
            marker_fill = QColor(self._accent)
            marker_fill.setAlpha(int(40 + self._marker_visible * 80))
            marker_line = QColor(self._accent)
            marker_line.setAlpha(int(120 + self._marker_visible * 110))
            p.setBrush(marker_fill)
            p.setPen(QPen(marker_line, 2))
            marker_radius = max(
                6.0, min(self._marker_rect.width(), self._marker_rect.height()) * 0.45
            )
            marker = QRectF(
                self._marker_rect.x() + self._jitter_x * 0.35,
                self._marker_rect.y() + self._jitter_y * 0.35,
                self._marker_rect.width(),
                self._marker_rect.height(),
            )
            p.drawRoundedRect(marker, marker_radius, marker_radius)

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
        elif self._action not in ("none", "center_float", "center_one_third"):
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
        self._target_rect = QRectF(0, 0, 0, 0)
        self._rect_velocity = [0.0, 0.0, 0.0, 0.0]
        self._is_morphing = False

        self._anim_timer = QTimer(self)
        self._anim_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._anim_timer.timeout.connect(self._on_anim_tick)
        self._elapsed = QElapsedTimer()

        self.hide()

    def set_refresh_rate(self, hz):
        clamped_hz = clamp_refresh_rate(hz)
        self._frame_interval_ms = compute_frame_interval_ms(clamped_hz)
        if self._anim_timer.isActive():
            self._anim_timer.start(self._frame_interval_ms)

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
            self._rect_velocity = [0.0, 0.0, 0.0, 0.0]
            self._apply_rect(self._current_rect)
            self._start_fade(1.0)
            return

        rect_changed = not self._rect_almost_equal(target_rect, self._target_rect)
        color_changed = next_color != self._target_color

        if rect_changed:
            self._target_rect = QRectF(target_rect)
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
            self._elapsed.restart()
            self._anim_timer.start(self._frame_interval_ms)

    def _on_anim_tick(self):
        dt = compute_dt(self._elapsed, self._frame_interval_ms)

        alpha_tau = 0.036
        alpha_blend = 1.0 - math.exp(-dt / alpha_tau)
        self._opacity = (
            self._opacity + (self._target_opacity - self._opacity) * alpha_blend
        )

        color_tau = 0.06
        color_blend = 1.0 - math.exp(-dt / color_tau)
        self._color = lerp_color(self._color, self._target_color, color_blend)

        if self._is_morphing:
            current_values = [
                self._current_rect.x(),
                self._current_rect.y(),
                self._current_rect.width(),
                self._current_rect.height(),
            ]
            target_values = [
                self._target_rect.x(),
                self._target_rect.y(),
                self._target_rect.width(),
                self._target_rect.height(),
            ]
            next_values = []
            morphing = False
            for index in range(4):
                current, velocity = spring_update(
                    current_values[index],
                    target_values[index],
                    self._rect_velocity[index],
                    SPRING_STIFFNESS,
                    SPRING_DAMPING,
                    dt,
                )
                if spring_done(current, target_values[index], velocity, pos_eps=0.35, vel_eps=1.0):
                    current = target_values[index]
                    velocity = 0.0
                else:
                    morphing = True
                next_values.append(current)
                self._rect_velocity[index] = velocity
            self._current_rect = QRectF(*next_values)
            self._apply_rect(self._current_rect)
            self._is_morphing = morphing

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
