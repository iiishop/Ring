<p align="center">
  <img src="logo.png" alt="Ring" width="96">
</p>

### Ring

按住左 Alt，往哪边滑鼠标，窗口就飞到哪边。不用拖标题栏，不用记快捷键。

> 支持 Windows 10+，多显示器自动适配。

---

### 怎么用

1. 按住**左 Alt**
2. 屏幕上出现一个圆环
3. 鼠标往八个方向滑动 —— 每个方向对应一种窗口布局
4. 松手，窗口到位

方向跟布局的关系：

| 滑向 | 效果 |
|------|------|
| 上下左右 | 半屏 |
| 四个角 | 四分屏 |
| 左右拉远一点 | 1/3 或 2/3 宽度 |
| 居中 | 最大化或浮窗 |

**Alt+Tab 不会误触。** 按住 Alt 再按别的键，Ring 会自己退下。

<!-- TODO: 录个 10 秒的 gif 丢进来，替换这一行 -->
<!-- ![](demo.gif) -->

---

### 下载

去 [Releases](https://github.com/iiishop/Ring/releases) 页面，每次发版都有两种包：

- **`Ring-portable-vX.X.X.zip`** —— 解压即用，啥也不用装
- **`Ring-vX.X.X-Setup.exe`** —— 安装版，会建开始菜单快捷方式

第一次运行会请求管理员权限（改窗口位置需要），授权后图标缩到右下角托盘。右键点图标可以退出。

---

### 长这样

> 截张图放这里

---

### 自己构建

```bash
git clone https://github.com/iiishop/Ring.git
cd Ring
pip install pyside6 pynput pygetwindow pyinstaller
pyinstaller Ring.spec
```

---

### 许可

MIT
