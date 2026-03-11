import tkinter as tk


class RingOverlayUI:
    def __init__(self, root, labels, icons):
        self.root = root
        self.labels = labels
        self.icons = icons
        self.fade_job = None
        self.current_alpha = 0.0

        self.action_var = tk.StringVar(value=labels["none"])
        self.icon_var = tk.StringVar(value=icons["none"])
        self._panel_size = 164

        self.sub_window = tk.Toplevel(root)
        self.sub_window.configure(bg="#010203")
        self.sub_window.wm_attributes("-transparentcolor", "#010203")
        self.sub_window.attributes("-alpha", 0)
        self.sub_window.overrideredirect(True)
        self.sub_window.attributes("-topmost", 1)
        self.sub_window.withdraw()

        card = tk.Canvas(
            self.sub_window,
            width=self._panel_size,
            height=self._panel_size,
            bg="#010203",
            bd=0,
            highlightthickness=0,
        )
        card.pack()
        card.create_oval(
            2,
            2,
            self._panel_size - 2,
            self._panel_size - 2,
            fill="#172233",
            outline="#2c425f",
            width=2,
        )

        title_label = tk.Label(
            self.sub_window,
            text="Ring Snap",
            fg="#9ec7ff",
            bg="#172233",
            font=("Segoe UI Semibold", 10),
        )
        title_label.place(relx=0.5, y=38, anchor="center")

        icon_label = tk.Label(
            self.sub_window,
            textvariable=self.icon_var,
            fg="#8cf2a5",
            bg="#172233",
            font=("Segoe UI Symbol", 30),
        )
        icon_label.place(relx=0.5, rely=0.47, anchor="center")

        self.action_label = tk.Label(
            self.sub_window,
            textvariable=self.action_var,
            fg="#9aa7bd",
            bg="#172233",
            font=("Segoe UI Semibold", 13),
        )
        self.action_label.place(relx=0.5, rely=0.73, anchor="center")

        self.target_preview = tk.Toplevel(root)
        self.target_preview.overrideredirect(True)
        self.target_preview.attributes("-topmost", 1)
        self.target_preview.attributes("-alpha", 0.18)
        self.target_preview.configure(bg="#6fd0ff")
        self.target_preview.withdraw()

    def get_rel(self, mouse_x, mouse_y):
        sub_center_x = self.sub_window.winfo_x() + self.sub_window.winfo_width() // 2
        sub_center_y = self.sub_window.winfo_y() + self.sub_window.winfo_height() // 2
        return mouse_x - sub_center_x, mouse_y - sub_center_y

    def center_at(self, mouse_x, mouse_y):
        self.root.update_idletasks()
        window_width = self._panel_size
        window_height = self._panel_size
        self.sub_window.geometry(
            f"+{mouse_x - window_width // 2}+{mouse_y - window_height // 2}"
        )

    def _update_target_preview(self, action, work_area, get_action_rect):
        if action == "none":
            self.target_preview.withdraw()
            return

        rect = get_action_rect(action, work_area)
        if rect is None:
            self.target_preview.withdraw()
            return

        x, y, width, height = rect
        if width <= 0 or height <= 0:
            self.target_preview.withdraw()
            return

        self.target_preview.geometry(f"{width}x{height}+{x}+{y}")
        self.target_preview.deiconify()
        self.target_preview.lift()
        self.sub_window.lift()

    def set_preview(self, action, work_area, get_action_rect, show_target=True):
        self.icon_var.set(self.icons[action])
        self.action_var.set(self.labels[action])
        if show_target:
            self._update_target_preview(action, work_area, get_action_rect)
        else:
            self.target_preview.withdraw()

        if action == "none":
            self.action_label.configure(fg="#9aa7bd")
        elif action == "maximize":
            self.action_label.configure(fg="#6fd0ff")
        else:
            self.action_label.configure(fg="#8cf2a5")

    def hide_target_preview(self):
        self.target_preview.withdraw()

    def animate_alpha(self, target_alpha, duration_ms=120, step_ms=10):
        if self.fade_job is not None:
            self.root.after_cancel(self.fade_job)
            self.fade_job = None

        start_alpha = self.current_alpha
        steps = max(1, duration_ms // step_ms)
        delta = (target_alpha - start_alpha) / steps

        if target_alpha > 0:
            self.sub_window.deiconify()

        def step(index):
            alpha = start_alpha + delta * index
            alpha = max(0.0, min(1.0, alpha))
            self.current_alpha = alpha
            self.sub_window.attributes("-alpha", alpha)

            if index < steps:
                self.fade_job = self.root.after(step_ms, lambda: step(index + 1))
            else:
                self.fade_job = None
                self.current_alpha = target_alpha
                self.sub_window.attributes("-alpha", target_alpha)
                if target_alpha <= 0:
                    self.sub_window.withdraw()

        step(1)

    def show_panel(self):
        self.animate_alpha(1.0)

    def hide_panel(self):
        self.animate_alpha(0.0)
