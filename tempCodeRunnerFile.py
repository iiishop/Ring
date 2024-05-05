import tkinter as tk

def update_label():
    x = root.winfo_pointerx()
    y = root.winfo_pointery()
    mouse_position.set(f"鼠标位置: ({x}, {y})")
    root.after(100, update_label)  # 每100毫秒更新一次

root = tk.Tk()
root.attributes('-fullscreen', True)  # 全屏
root.attributes('-alpha', 0)  # 设置透明度
root.overrideredirect(True)  # 去掉标题栏

# 创建一个不透明的子窗口
sub_window = tk.Toplevel(root)
sub_window.attributes('-alpha', 1)  # 设置透明度
sub_window.overrideredirect(True)  # 去掉标题栏

# 创建一个标签
mouse_position = tk.StringVar()
label = tk.Label(sub_window, textvariable=mouse_position)
label.pack()

# 创建一个按钮
button = tk.Button(sub_window, text="这是一个按钮")
button.pack()

update_label()  # 开始更新标签

root.mainloop()