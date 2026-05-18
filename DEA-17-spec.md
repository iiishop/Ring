# DEA-17: 动画丝滑跟手优化

## 问题诊断

Ring 按住 Alt 时显示圆环 overlay（LiquidOverlayWidget, 188x188），鼠标相对 overlay 中心的方向/距离决定目标 action（左半屏、右1/3等）。当前动画存在三个阻塞手感的问题：

### 痛点1: 离散 action 无滞后 → 边界抖动
`calculate_action()` 返回离散值。鼠标在阈值附近（如 left_half ↔ left_one_third 的 edge_progress ≈ 0.42）来回晃时，每帧触发 `set_action()` → 重置 `_transition_t = 0.0` → transition 动画永远跑不完 → 抽搐感。

### 痛点2: 固定时长 smootherstep 被打断 → 跳帧
当前 transition 是 92ms 的 smootherstep。动画被打断后从头开始，快速扫过多个区域时连续跳帧。

### 痛点3: 三个独立 Timer 漂移 → 微颤
LiquidOverlayWidget 的 `_pulse_timer`、`_transition_timer`、`_fade_timer` 各自独立运行，pulse phase 按 `_frame_interval_ms` 假设推进，但实际 tick 间隔有微小偏差（系统调度误差），导致 FBM 噪声微动与屏幕刷新率不同步时产生可见微颤。

TargetPreviewWidget 同理：矩形 morphing 82ms 固定时长，同样会被频繁打断。

## 改进方案

### 1. Hysteresis（滞后防抖）
在 `LiquidOverlayWidget` 中维护候选 action 和连续帧计数器。只有候选 action 连续 3 帧不变时才真正切换。

位置：`LiquidOverlayWidget.set_action()` 的调用侧。具体逻辑可放在新方法 `set_action_stable(action)` 中，由 `main.py` 的 `on_update_tick()` 调用。

```python
_candidate_action: str
_candidate_frames: int = 0
HYSTERESIS_FRAMES: int = 3  # 连续确认帧数

def set_action_stable(self, action):
    if action == self._candidate_action:
        self._candidate_frames += 1
        if self._candidate_frames >= self.HYSTERESIS_FRAMES and action != self._action:
            self.set_action(action)
    else:
        self._candidate_action = action
        self._candidate_frames = 1
```

`main.py` 中 `update_preview()` → `overlay.set_action(action)` 改为 `overlay.set_action_stable(action)`。

`TargetPreviewWidget.show_preview()` 不需要 hysteresis（它是被动响应，不是高频轮询）。

### 2. Spring-based transition（弹簧物理替代固定时长 smootherstep）
用弹簧物理模拟替代 `_transition_timer` + `smootherstep`。弹簧特性：动画被中断后从当前位置自然衰减到新目标，不会跳变。

LiquidOverlayWidget 需要弹簧的属性：
- `_accent` (QColor) → 4 个分量各自用弹簧（r, g, b, a 用同一套 stiffness/damping）
- `_angle` (float) → 单弹簧
- `_marker_rect` (QRectF) → 4 个分量（x, y, w, h）各自用弹簧
- `_marker_visible` (float) → 单弹簧

参数（经过调参会比常量更好）：
```python
SPRING_STIFFNESS = 200.0  # 刚度
SPRING_DAMPING = 20.0     # 阻尼（接近临界阻尼，无振荡）
```

不使用 `_transition_timer`。在主 refresh tick 中每帧更新弹簧状态：
```python
def _spring_update(self, current, target, velocity, stiffness, damping, dt):
    force = -stiffness * (current - target)
    velocity += force * dt
    velocity *= math.exp(-damping * dt)
    current += velocity * dt
    return current, velocity
```

TargetPreviewWidget 的矩形 morphing（`_is_morphing` → `_from_rect` → `_to_rect`）同样替换为 spring-based。

### 3. 统一 Timer + 真实 delta time
合并 LiquidOverlayWidget 的三个 Timer 为一个 `_refresh_timer`。使用 `QElapsedTimer` 测量两次 tick 之间的真实 dt（毫秒 → 秒），而不是假设 `_frame_interval_ms` 精确。

```python
from PySide6.QtCore import QElapsedTimer

self._refresh_timer = QTimer(self)
self._refresh_timer.setTimerType(Qt.TimerType.PreciseTimer)
self._refresh_timer.timeout.connect(self._on_refresh_tick)
self._elapsed = QElapsedTimer()

def _on_refresh_tick(self):
    dt = self._elapsed.elapsed() / 1000.0  # 真实 delta time
    self._elapsed.restart()
    
    # ---- 原 _on_pulse_tick 逻辑 ----
    self._pulse_phase += dt * 2.35
    self._time_s += dt
    # ... jitter 计算 ...
    
    # ---- 原 _on_transition_tick 逻辑 (spring) ----
    # 如果 _action 未到达目标 → spring update
    
    # ---- 原 _on_fade_tick 逻辑 ----
    # 如果 _fade_steps_left > 0 → fade step
    
    self.update()
```

- 显隐时 `_refresh_timer` 保持运行（不再用独立的 fade timer），但 pulse 只在 `_panel_alpha > 0` 时更新。
- 动画完全结束后且已隐藏（`_panel_alpha <= 0`），stop timer。

TargetPreviewWidget 已经只有一个 `_anim_timer`，主要改动：
- 加 `QElapsedTimer` 测真实 dt
- 矩形 morphing 从 smootherstep 改为 spring-based
- 保持 alpha 和 color 的指数平滑（这两个已经用真实 dt 了，不用改）

## 涉及文件
- `ui.py`：主要修改，LiquidOverlayWidget 和 TargetPreviewWidget
- `main.py`：`update_preview()` 中 `overlay.set_action()` → `overlay.set_action_stable()`

## 验收标准
1. 鼠标在 action 边界上来回晃时，overlay marker 不再抖动
2. 快速扫过多个 action 区域时，动画跟随流畅，无明显跳帧
3. overlay 微动（jitter）在不同刷新率显示器上平滑无颤
4. 不引入新的视觉闪烁或性能退化
5. 保持现有所有 action 的功能正确性
6. 完成后运行一次 `python main.py` 确认能启动无报错

## 不要做的
- 不要改 calculate_action() 的阈值逻辑
- 不要改 apply_window_action() 的窗口操作
- 不要改键盘监听（pynput）相关代码
- 不要动 RECT.py 和 tools.py
