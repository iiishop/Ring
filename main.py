import math
import tkinter as tk
from pynput import keyboard
import pygetwindow as gw
from screeninfo import get_monitors
from pywinauto import Application
import time

alt_pressed = False
active_window = None
app = None
windwo = None
screen_width = 192
screen_height = 108

def get_mouse_position():
    x = root.winfo_pointerx()
    y = root.winfo_pointery()
    return x, y

def det_rel():
    x, y = get_mouse_position()
    sub_center_x = sub_window.winfo_x() + sub_window.winfo_width() // 2
    sub_center_y = sub_window.winfo_y() + sub_window.winfo_height() // 2
    rel_x = x - sub_center_x
    rel_y = y - sub_center_y
    return rel_x, rel_y

def get_mouse_monitor(x, y):
    for m in get_monitors():
        if m.x <= x < m.x + m.width and m.y <= y < m.y + m.height:
            return m
    return None

def update_label():
    rel_x, rel_y = det_rel()
    mouse_position.set(f"相对位置: ({rel_x}, {rel_y})")
    root.after(100, update_label)  # 每100毫秒更新一次

def on_alt_press(key):
    global alt_pressed, active_window, screen_width, screen_height, app, window
    if key == keyboard.Key.alt_l and not alt_pressed:
        print("按下Alt键")
        active_window = gw.getActiveWindow()
        print(active_window.title)
        #if(active_window.title == "Ring"):
        #    print("当前窗口是Ring")
        #    all_windows = sorted(gw.getAllWindows(), key=lambda x: x.zorder)
        #    active_window_index = all_windows.index(active_window)
        #    if(active_window_index > 0):
        #        active_window = all_windows[active_window_index - 1]
        #        print(active_window.title)
        #    else:
        #        active_window = None
        #        print("没有找到其他窗口")
        screen_height = get_mouse_monitor(*get_mouse_position()).height
        screen_width = get_mouse_monitor(*get_mouse_position()).width
        
        x, y = get_mouse_position()
        sub_window.geometry(f"+{x-sub_window.winfo_width()//2}+{y-sub_window.winfo_height()//2}")  # 移动子窗口的位置
        
        sub_window.deiconify()
        alt_pressed = True
    
def on_alt_release(key):
    global alt_pressed
    if (key == keyboard.Key.alt_l):
        print("释放Alt键")
        rel_x, rel_y = det_rel()
        if(not active_window.title == "Ring"):
            if(rel_x**2 + rel_y**2 > 50**2):
                #获取x、y组成向量的角度
                angle = math.degrees(math.acos(rel_x / math.sqrt(rel_x**2 + rel_y**2)))
                print(angle)
                print("移动窗口")

                if rel_x > 0 and rel_y > 0 or rel_x < 0 and rel_y > 0:
                    angle = 360 - angle
                print(angle)
                    
                if(angle < 22.5 or angle > 337.5):
                    print("右半屏")
                    #将窗口变为右半分屏
                    active_window.restore()
                    active_window.resizeTo(screen_width//2, screen_height)
                    active_window.moveTo(screen_width//2, 0)
                elif(angle >=22.5 and angle < 67.5):
                    print("右上角")
                    active_window.restore()
                    active_window.resizeTo(screen_width//2, screen_height//2)
                    active_window.moveTo(screen_width//2, 0)
                elif(angle >=67.5 and angle < 112.5):
                    print("上半屏")
                    #将窗口变为上半分屏
                    active_window.restore()
                    active_window.resizeTo(screen_width, screen_height//2)
                    active_window.moveTo(0, 0)
                elif(angle >=112.5 and angle < 157.5):
                    print("左上角")
                    active_window.restore()
                    active_window.resizeTo(screen_width//2, screen_height//2)
                    active_window.moveTo(0, 0)
                elif(angle >=157.5 and angle < 202.5):
                    print("左半屏")
                    #将窗口变为左半分屏
                    active_window.restore()
                    active_window.resizeTo(screen_width//2, screen_height)
                    active_window.moveTo(0, 0)
                elif(angle >=202.5 and angle < 247.5):
                    print("左下角")
                    active_window.restore()
                    active_window.resizeTo(screen_width//2, screen_height//2)
                    active_window.moveTo(0, screen_height//2)
                elif(angle >=247.5 and angle < 292.5):
                    print("下半屏")
                    #将窗口变为下半分屏
                    active_window.restore()
                    active_window.resizeTo(screen_width, screen_height//2)
                    active_window.moveTo(0, screen_height//2)
                elif(angle >=292.5 and angle < 337.5):
                    print("右下角")
                    active_window.restore()
                    active_window.resizeTo(screen_width//2, screen_height//2)
                    active_window.moveTo(screen_width//2, screen_height//2)
                else:
                    pass
        
        sub_window.withdraw()
        alt_pressed = False

def on_button_press():
    print("点击按钮")
    return "break"  # 阻止事件继续传递


root = tk.Tk()
root.title("Ring")
#root.attributes('-fullscreen', True)  # 全屏
root.attributes('-alpha', 0)  # 设置透明度
#root.overrideredirect(True)  # 去掉标题栏

x = root.winfo_pointerx()
y = root.winfo_pointery()

# 创建一个不透明的子窗口
sub_window = tk.Toplevel(root)
sub_window.attributes('-alpha', 1)  # 设置透明度
sub_window.overrideredirect(True)  # 去掉标题栏
sub_window.attributes('-topmost', 1)
sub_window.withdraw()  # 隐藏子窗口

# 创建一个标签
mouse_position = tk.StringVar()
label = tk.Label(sub_window, textvariable=mouse_position)
label.pack()

# 创建一个按钮
button = tk.Button(sub_window, text="这是一个按钮", command=on_button_press)
button.pack()

listener = keyboard.Listener(on_press=on_alt_press, on_release=on_alt_release)
listener.start()

update_label()  # 开始更新标签

root.mainloop()