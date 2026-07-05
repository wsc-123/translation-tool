import keyboard
import json
try:
    import mouse
except ImportError:
    mouse = None
import pyperclip
from winotify import Notification
import time
import sys
import os
import ctypes
from pathlib import Path

# 将当前脚本所在目录添加到 Python 路径
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from translator import BaiduTranslator, ConfigError


class TranslationHotkey:
    def __init__(self):
        """初始化快捷键监听器"""
        try:
            self.translator = BaiduTranslator()
        except ConfigError as e:
            print(f"配置错误: {e}")
            self.show_notification("配置错误", str(e))
            raise SystemExit(1) from e

        self.last_trigger_time = 0
        self.cooldown = 0.5  # 防止重复触发，冷却时间0.5秒
        self.hotkeys = self.load_hotkeys()
        self.clipboard_hotkey = self.hotkeys.get('clipboard_translate', 'f9')
        self.selection_mouse_button = self.hotkeys.get('selection_translate_mouse_button', 'x2')
        self.exit_hotkey = self.hotkeys.get('exit', 'ctrl+shift+q')

    def load_hotkeys(self):
        """从 config.json 加载快捷键配置。"""
        defaults = {
            'clipboard_translate': 'f9',
            'selection_translate_mouse_button': 'x2',
            'exit': 'ctrl+shift+q',
        }

        try:
            config_path = SCRIPT_DIR / 'config.json'
            with config_path.open('r', encoding='utf-8') as f:
                config = json.load(f)
            defaults.update(config.get('hotkeys', {}))
        except Exception:
            pass

        return defaults

    def can_trigger(self):
        """检查是否处于冷却时间外。"""
        current_time = time.time()

        if current_time - self.last_trigger_time < self.cooldown:
            return False

        self.last_trigger_time = current_time
        return True

    def translate_text(self, text, empty_message="剪贴板为空"):
        """翻译指定文本并把结果写入剪贴板。"""
        if not text.strip():
            self.show_notification("提示", empty_message)
            return

        # 显示翻译中通知
        self.show_notification("翻译中...", f"正在翻译: {text[:50]}...")

        # 调用翻译
        translated = self.translator.translate(text)

        if translated.startswith(("翻译失败", "翻译出错")):
            self.show_notification("翻译失败", translated[:100])
            return

        # 将翻译结果写入剪贴板
        pyperclip.copy(translated)

        # 显示翻译结果
        self.show_notification("翻译完成", f"结果: {translated[:100]}")

    def translate_clipboard(self):
        """翻译剪贴板内容"""
        if not self.can_trigger():
            return

        try:
            # 获取剪贴板内容
            text = pyperclip.paste()
            self.translate_text(text)

        except Exception as e:
            self.show_notification("错误", f"翻译失败: {str(e)}")

    def translate_selection(self):
        """复制当前选中文本并翻译。"""
        if not self.can_trigger():
            return

        try:
            previous_sequence = self.get_clipboard_sequence()
            keyboard.press_and_release('ctrl+c')
            text = self.wait_for_clipboard_text(previous_sequence)
            self.translate_text(text, "未检测到可复制的选中文本")

        except Exception as e:
            self.show_notification("错误", f"复制并翻译失败: {str(e)}")

    def get_clipboard_sequence(self):
        """获取 Windows 剪贴板序号，用来判断 Ctrl+C 是否真的更新了剪贴板。"""
        return ctypes.windll.user32.GetClipboardSequenceNumber()

    def wait_for_clipboard_text(self, previous_sequence, timeout=0.8):
        """等待 Ctrl+C 更新剪贴板，并返回文本内容。"""
        deadline = time.time() + timeout

        while time.time() < deadline:
            if self.get_clipboard_sequence() != previous_sequence:
                return pyperclip.paste()
            time.sleep(0.05)

        return ""

    def show_notification(self, title, message):
        """显示Windows通知"""
        try:
            toast = Notification(
                app_id="翻译助手",
                title=title,
                msg=message,
                duration="short"
            )
            toast.show()
        except Exception as e:
            print(f"通知显示失败: {e}")

    def start(self):
        """启动快捷键监听"""
        print("翻译助手已启动！")
        print("使用方法：")
        print(f"1. 复制中文文本 (Ctrl+C)，按 {self.clipboard_hotkey.upper()} 翻译剪贴板")
        print("2. 选中文本，按鼠标上侧键自动复制并翻译")
        print("3. 翻译结果自动复制到剪贴板")
        print(f"\n按 {self.exit_hotkey.upper()} 退出程序\n")

        # 注册快捷键
        keyboard.add_hotkey(self.clipboard_hotkey, self.translate_clipboard)
        keyboard.add_hotkey(self.exit_hotkey, lambda: self.stop())

        if mouse is None:
            print("未安装 mouse 库，鼠标侧键功能不可用。请运行 pip install -r requirements.txt")
        else:
            mouse.on_button(
                self.translate_selection,
                buttons=(self.selection_mouse_button,),
                types=('down',)
            )

        # 保持程序运行
        keyboard.wait()

    def stop(self):
        """停止程序"""
        print("\n翻译助手已退出")
        keyboard.unhook_all()
        if mouse is not None:
            mouse.unhook_all()
        exit(0)


if __name__ == '__main__':
    app = TranslationHotkey()
    app.start()
