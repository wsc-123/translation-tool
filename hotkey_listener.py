import keyboard
import pyperclip
from winotify import Notification
import time
import sys
import os

# 将当前脚本所在目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from translator import BaiduTranslator


class TranslationHotkey:
    def __init__(self):
        """初始化快捷键监听器"""
        self.translator = BaiduTranslator()
        self.last_trigger_time = 0
        self.cooldown = 0.5  # 防止重复触发，冷却时间0.5秒

    def translate_clipboard(self):
        """翻译剪贴板内容"""
        current_time = time.time()

        # 防止短时间内重复触发
        if current_time - self.last_trigger_time < self.cooldown:
            return

        self.last_trigger_time = current_time

        try:
            # 获取剪贴板内容
            text = pyperclip.paste()

            if not text.strip():
                self.show_notification("提示", "剪贴板为空")
                return

            # 显示翻译中通知
            self.show_notification("翻译中...", f"正在翻译: {text[:50]}...")

            # 调用翻译
            translated = self.translator.translate(text)

            # 将翻译结果写入剪贴板
            pyperclip.copy(translated)

            # 显示翻译结果
            self.show_notification("翻译完成", f"结果: {translated[:100]}")

        except Exception as e:
            self.show_notification("错误", f"翻译失败: {str(e)}")

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
        print("1. 复制中文文本 (Ctrl+C)")
        print("2. 按 F9 翻译")
        print("3. 翻译结果自动复制到剪贴板")
        print("\n按 Ctrl+Shift+Q 退出程序\n")

        # 注册快捷键
        keyboard.add_hotkey('f9', self.translate_clipboard)
        keyboard.add_hotkey('ctrl+shift+q', lambda: self.stop())

        # 保持程序运行
        keyboard.wait()

    def stop(self):
        """停止程序"""
        print("\n翻译助手已退出")
        keyboard.unhook_all()
        exit(0)


if __name__ == '__main__':
    app = TranslationHotkey()
    app.start()
