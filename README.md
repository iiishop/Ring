<p align="center">
  <img src="logo.png" alt="Ring" width="128">
</p>

<h1 align="center">Ring</h1>
<p align="center"><strong>按住 Alt，滑动鼠标，窗口归位。</strong></p>
<p align="center">一个极简的 Windows 窗口吸附工具 —— 用圆环手势替代拖拽和快捷键。</p>

<p align="center">
  <img src="https://img.shields.io/github/v/release/iiishop/Ring?color=%2393c5fd" alt="release">
  <img src="https://img.shields.io/badge/platform-Windows%2010%2B-blue" alt="platform">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
</p>

<!-- TODO: 替换为 10 秒演示 GIF -->
<!-- <p align="center">
  <img src="demo.gif" alt="Ring demo" width="600">
</p> -->

---

## 这是什么

用鼠标拖动窗口到屏幕边缘太慢，Win+方向键要离开鼠标。Ring 让你**按住左 Alt 不放**，屏幕上出现一个圆环，**鼠标滑向哪个方向，窗口就吸附到哪个位置**——松手即定位。

支持 14 种布局：半屏、1/3、2/3、四角、居中浮窗、最大化。多显示器自动适配，动画流畅跟手。

## 快速开始

从 [Releases](https://github.com/iiishop/Ring/releases) 下载最新版：

| 版本 | 说明 |
|------|------|
| **便携版** `Ring-portable-v*.zip` | 解压即用，无需安装 |
| **安装版** `Ring-v*-Setup.exe` | NSIS 安装包，创建开始菜单快捷方式 |

运行后，Ring 会请求管理员权限（窗口操作需要），然后**最小化到系统托盘**。右键托盘图标可退出。

## 使用方式

1. **按住左 Alt** → 屏幕出现圆环浮层，锚定在鼠标位置
2. **移动鼠标** → 圆环上的高亮弧线跟手转动，目标区域预览同步显示
3. **对准方向后松开 Alt** → 窗口自动吸附，预览消失

| 鼠标方向 | 窗口布局 |
|----------|----------|
| ↑ | 上半屏 |
| ↓ | 下半屏 |
| ← | 左半屏 |
| → | 右半屏 |
| ↖ | 左上角 |
| ↗ | 右上角 |
| ↙ | 左下角 |
| ↘ | 右下角 |

**进阶手势：** 在左/右方向拉得更远可切换 1/3 或 2/3 宽度；向上/下方向拉远触发居中 1/3 宽度；居中区域触发浮窗或最大化。

> **提示：** 左 Alt 只在**单独按下**时触发 Ring，Alt+Tab / Alt+F4 等组合键不会误触。

## 特性

- 🎯 **14 种窗口布局** —— 半屏、1/3、2/3、四角、浮窗、最大化
- 🖥️ **多显示器适配** —— 根据鼠标所在屏幕自动计算工作区
- 🎨 **Fluent Design 风格** —— 磨砂玻璃圆环、弹性动画、柔光效果
- ⚡ **弹簧物理动画** —— 颜色和形状过渡自然跟手，不跳帧
- 🔒 **防误触** —— Alt 组合键（Alt+Tab 等）不会激活 Ring
- 📦 **零依赖运行** —— 单文件 exe，解压即用

## 构建

```bash
git clone https://github.com/iiishop/Ring.git
cd Ring
pip install pyside6 pynput pygetwindow pyinstaller
pyinstaller --noconfirm --clean Ring.spec
# 输出在 dist/Ring.exe
```

## 许可

MIT © [iiishop](https://github.com/iiishop)
