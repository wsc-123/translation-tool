# 一键翻译助手 | Quick Translation Tool

一个基于百度翻译 API 的 Windows 桌面快捷翻译工具，支持全局快捷键一键翻译剪贴板内容。

A Windows desktop translation tool based on Baidu Translate API, supporting global hotkey for instant clipboard translation.

---

## ✨ 功能特点 | Features

- 📋 **剪贴板翻译**：复制文本后按快捷键自动翻译
- 🔔 **通知提醒**：Windows 桌面通知显示翻译结果
- ⌨️ **全局快捷键**：`F9` 触发翻译（可自定义）
- 🚀 **快速便捷**：翻译结果自动复制到剪贴板，直接粘贴使用
- 🔒 **隐私安全**：本地运行，数据仅用于翻译

---

## 📦 项目结构 | Project Structure

```
Language change project/
│
├── config.json              # API 配置文件
├── translator.py            # 百度翻译核心逻辑
├── hotkey_listener.py       # 快捷键监听主程序
├── requirements.txt         # Python 依赖包列表
├── 启动翻译助手.bat          # Windows 启动脚本
└── README.md                # 项目说明文档
```

---

## 🛠️ 安装步骤 | Installation

### 1. 克隆项目

```bash
git clone https://github.com/your-username/translation-tool.git
cd translation-tool
```

### 2. 安装 Python

- 下载并安装 [Python 3.11+](https://www.python.org/downloads/)
- 或使用便携版 Python（解压到 `C:\Python` 目录）

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置 API

编辑 `config.json`，填入你的百度翻译 API 密钥：

```json
{
  "baidu": {
    "app_id": "你的百度翻译APP_ID",
    "secret_key": "你的百度翻译密钥"
  },
  "translation": {
    "from_lang": "zh",
    "to_lang": "en"
  }
}
```

**获取百度翻译 API：**
1. 访问 [百度翻译开放平台](https://fanyi-api.baidu.com/)
2. 注册并创建应用
3. 获取 APP ID 和密钥

---

## 🚀 使用方法 | Usage

### 启动程序

**方法 1：双击启动脚本**
```
双击运行 "启动翻译助手.bat"
```

**方法 2：命令行启动**
```bash
python hotkey_listener.py
```

**注意**：需要**管理员权限**才能使全局快捷键生效。

### 翻译流程

1. **启动程序**：运行启动脚本或命令
2. **复制文本**：选中中文文本，按 `Ctrl+C` 复制
3. **触发翻译**：按 `F9`
4. **查看结果**：
   - 桌面右下角弹出通知显示翻译结果
   - 翻译结果已自动复制到剪贴板
5. **粘贴使用**：按 `Ctrl+V` 直接粘贴英文翻译

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| `F9` | 翻译剪贴板内容 |
| `Ctrl+Shift+Q` | 退出程序 |

---

## ⚙️ 自定义配置 | Customization

### 修改快捷键

编辑 `hotkey_listener.py`，找到以下代码并修改：

```python
# 注册快捷键
keyboard.add_hotkey('F9', self.translate_clipboard)  # 修改 'F9' 为你想要的快捷键
keyboard.add_hotkey('ctrl+shift+q', lambda: self.stop())
```

### 修改翻译语言

编辑 `config.json`：

```json
{
  "translation": {
    "from_lang": "zh",    # 源语言：zh=中文, en=英文, jp=日语等
    "to_lang": "en"       # 目标语言
  }
}
```

**语言代码参考**：
- `zh` - 中文
- `en` - 英文
- `jp` - 日语
- `kor` - 韩语
- `fra` - 法语
- `spa` - 西班牙语

更多语言代码请参考 [百度翻译语言列表](https://fanyi-api.baidu.com/product/113)

---

## 📋 依赖包 | Dependencies

```
requests       # HTTP 请求库
keyboard       # 全局快捷键监听
pyperclip      # 剪贴板操作
winotify       # Windows 通知
```

---

## 💡 开机自启动（可选）| Auto-start

1. 右键 `启动翻译助手.bat` 创建快捷方式
2. 按 `Win+R`，输入 `shell:startup` 打开启动文件夹
3. 将快捷方式放入该文件夹

---

## ⚠️ 注意事项 | Notes

- 需要管理员权限运行以使全局快捷键生效
- 确保网络连接正常（需访问百度翻译 API）
- 支持多行文本翻译
- 百度翻译 API 有调用频率限制（标准版 QPS=1）

---

## 🔧 故障排除 | Troubleshooting

### 快捷键无响应
- 以管理员身份运行程序
- 检查快捷键是否与其他程序冲突

### 翻译失败
- 检查网络连接
- 确认 API 密钥配置正确
- 查看百度翻译 API 额度是否用尽

### 通知不显示
- 检查 Windows 通知设置是否开启
- 确认 winotify 已正确安装

---

## 📄 许可证 | License

MIT License

---

## 🙏 致谢 | Acknowledgments

- [百度翻译开放平台](https://fanyi-api.baidu.com/)
- [keyboard](https://github.com/boppreh/keyboard)
- [pyperclip](https://github.com/asweigart/pyperclip)
- [winotify](https://github.com/verillious/winotify)
  (https://linux.do/)

---

## 📧 联系方式 | Contact

如有问题或建议，欢迎提交 Issue 或 Pull Request。

---

**使用愉快！Enjoy translating!** 🎉
