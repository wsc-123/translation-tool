import keyboard
import json
import queue
import re
import threading
try:
    import mouse
except ImportError:
    mouse = None
try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    tk = None
    ttk = None
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

        self.config = self.load_config()
        self.hotkeys = self.load_hotkeys()
        self.auto_translate = self.load_auto_translate_config()
        self.clipboard_hotkey = self.hotkeys.get('clipboard_translate', 'f9')
        self.selection_mouse_button = self.hotkeys.get('selection_translate_mouse_button', 'x2')
        self.exit_hotkey = self.hotkeys.get('exit', 'ctrl+shift+q')
        self.last_trigger_time = 0
        self.cooldown = 0.5  # 防止重复触发，冷却时间0.5秒
        self.stop_event = threading.Event()
        self.ui_queue = queue.Queue()
        self.root = None
        self.current_popup = None
        self.last_auto_clipboard_text = ""
        self.ignored_clipboard_texts = []
        self.clipboard_state_lock = threading.Lock()
        self.auto_suspended_until = 0
        self.auto_translation_lock = threading.Lock()
        self.dpi_awareness_enabled = False

    def load_config(self):
        """加载 config.json。"""
        try:
            config_path = SCRIPT_DIR / 'config.json'
            with config_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def load_hotkeys(self):
        """从 config.json 加载快捷键配置。"""
        defaults = {
            'clipboard_translate': 'f9',
            'selection_translate_mouse_button': 'x2',
            'exit': 'ctrl+shift+q',
        }

        defaults.update(self.config.get('hotkeys', {}))

        return defaults

    def load_auto_translate_config(self):
        """加载英文剪贴板自动翻译配置。"""
        defaults = {
            'enabled': True,
            'from_lang': 'en',
            'to_lang': 'zh',
            'min_length': 10,
            'min_words': 2,
            'min_letter_ratio': 0.45,
            'poll_interval': 0.3,
            'popup_seconds': 0,
        }
        defaults.update(self.config.get('auto_translate', {}))
        return defaults

    def can_trigger(self):
        """检查是否处于冷却时间外。"""
        current_time = time.time()

        if current_time - self.last_trigger_time < self.cooldown:
            return False

        self.last_trigger_time = current_time
        return True

    def translate_text(
        self,
        text,
        empty_message="剪贴板为空",
        from_lang=None,
        to_lang=None,
        copy_result=True,
        show_result_notification=True,
    ):
        """翻译指定文本并把结果写入剪贴板。"""
        if not text.strip():
            self.show_notification("提示", empty_message)
            return ""

        # 显示翻译中通知
        self.show_notification("翻译中...", f"正在翻译: {text[:50]}...")

        # 调用翻译
        translated = self.translator.translate(text, from_lang=from_lang, to_lang=to_lang)

        if translated.startswith(("翻译失败", "翻译出错")):
            self.show_notification("翻译失败", translated[:100])
            return ""

        if copy_result:
            # 将翻译结果写入剪贴板
            pyperclip.copy(translated)
            self.remember_ignored_clipboard_text(translated)

        if show_result_notification:
            # 显示翻译结果
            self.show_notification("翻译完成", f"结果: {translated[:100]}")

        return translated

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
            self.suspend_auto_translate(1.5)
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

    def remember_ignored_clipboard_text(self, text):
        """记录程序自己写入剪贴板的文本，避免被自动翻译监听再次处理。"""
        if not text:
            return

        with self.clipboard_state_lock:
            self.ignored_clipboard_texts.append(text)
            self.ignored_clipboard_texts = self.ignored_clipboard_texts[-10:]

    def should_ignore_clipboard_text(self, text):
        """判断当前剪贴板文本是否是程序自己写入的内容。"""
        with self.clipboard_state_lock:
            if text in self.ignored_clipboard_texts:
                self.ignored_clipboard_texts.remove(text)
                return True

        return False

    def suspend_auto_translate(self, seconds):
        """短时间暂停自动翻译，用于手动快捷键内部复制流程。"""
        self.auto_suspended_until = max(self.auto_suspended_until, time.time() + seconds)

    def start_auto_clipboard_monitor(self):
        """启动后台剪贴板监听。"""
        if not self.auto_translate.get('enabled', True):
            print("英文自动弹窗翻译：已关闭")
            return

        if tk is None:
            print("未检测到 tkinter，英文自动弹窗翻译功能不可用。")
            return

        monitor = threading.Thread(target=self.clipboard_monitor_loop, daemon=True)
        monitor.start()
        print(
            "英文自动弹窗翻译：已开启 "
            f"(最少 {self.auto_translate.get('min_length', 3)} 字符 / "
            f"{self.auto_translate.get('min_words', 1)} 个英文词)"
        )

    def clipboard_monitor_loop(self):
        """监听剪贴板变化，并处理新复制的英文文本。"""
        last_sequence = self.get_clipboard_sequence()
        poll_interval = float(self.auto_translate.get('poll_interval', 0.3))

        while not self.stop_event.wait(poll_interval):
            try:
                current_sequence = self.get_clipboard_sequence()
                if current_sequence == last_sequence:
                    continue

                last_sequence = current_sequence
                text = pyperclip.paste()
                self.handle_clipboard_change(text)
            except Exception:
                continue

    def handle_clipboard_change(self, text):
        """处理剪贴板新文本。"""
        text = self.normalize_clipboard_text(text)

        if not text:
            return

        if time.time() < self.auto_suspended_until:
            return

        if self.should_ignore_clipboard_text(text):
            return

        if text == self.last_auto_clipboard_text:
            return

        if not self.is_probably_english_text(text):
            return

        self.last_auto_clipboard_text = text
        worker = threading.Thread(target=self.translate_auto_clipboard_text, args=(text,), daemon=True)
        worker.start()

    def translate_auto_clipboard_text(self, text):
        """自动把英文剪贴板内容翻译成中文并弹窗。"""
        if not self.auto_translation_lock.acquire(blocking=False):
            return

        try:
            translated = self.translator.translate(
                text,
                from_lang=self.auto_translate.get('from_lang', 'en'),
                to_lang=self.auto_translate.get('to_lang', 'zh'),
            )

            if translated.startswith(("翻译失败", "翻译出错")):
                self.show_notification("自动翻译失败", translated[:100])
                return

            self.queue_translation_popup(text, translated)
        finally:
            self.auto_translation_lock.release()

    def normalize_clipboard_text(self, text):
        """整理剪贴板文本，减少重复空白导致的误判。"""
        if not isinstance(text, str):
            return ""

        return re.sub(r'\s+', ' ', text).strip()

    def is_probably_english_text(self, text):
        """用保守规则判断文本是否适合自动英文翻译。"""
        min_length = int(self.auto_translate.get('min_length', 10))
        min_words = int(self.auto_translate.get('min_words', 2))
        min_letter_ratio = float(self.auto_translate.get('min_letter_ratio', 0.45))

        if len(text) < min_length:
            return False

        if re.search(r'[\u4e00-\u9fff]', text):
            return False

        if self.looks_like_url_or_path(text):
            return False

        if self.looks_like_code(text):
            return False

        letters = sum(1 for ch in text if ch.isascii() and ch.isalpha())
        if letters / max(len(text), 1) < min_letter_ratio:
            return False

        words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text)
        if len(words) < min_words:
            return False

        return True

    def looks_like_url_or_path(self, text):
        """排除网址和常见文件路径。"""
        if re.match(r'^(https?://|www\.)', text, re.IGNORECASE):
            return True

        if re.match(r'^[A-Za-z]:[\\/]', text):
            return True

        if text.startswith(('\\\\', '/')) and ' ' not in text:
            return True

        slash_count = text.count('/') + text.count('\\')
        if slash_count >= 2 and ' ' not in text:
            return True

        return False

    def looks_like_code(self, text):
        """排除明显像代码的文本。"""
        code_symbols = sum(1 for ch in text if ch in '{}[]();=<>`|')
        strong_code_symbols = sum(1 for ch in text if ch in '{}[]=<>`|')
        if strong_code_symbols >= 3:
            return True

        code_keywords = r'\b(def|class|import|return|function|const|let|var)\b'
        if re.search(code_keywords, text) and code_symbols >= 2:
            return True

        control_keywords = r'\b(if|else|for|while)\b'
        if re.search(control_keywords, text) and (strong_code_symbols >= 1 or ';' in text):
            return True

        if ';' in text and re.search(r'[A-Za-z_][A-Za-z0-9_]*\s*=', text):
            return True

        if '\n' in text and any(line.strip().endswith(('{', ';')) for line in text.splitlines()):
            return True

        return False

    def setup_ui(self):
        """初始化隐藏的 tkinter 根窗口，用于显示翻译弹窗。"""
        if tk is None:
            return

        self.enable_dpi_awareness()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.after(100, self.process_ui_queue)

    def enable_dpi_awareness(self):
        """让 Windows 按原生 DPI 渲染 Tk 窗口，减少高分屏模糊。"""
        if self.dpi_awareness_enabled:
            return

        self.dpi_awareness_enabled = True
        if os.name != 'nt':
            return

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    def process_ui_queue(self):
        """在主线程处理 UI 任务。"""
        should_stop = False

        while True:
            try:
                item = self.ui_queue.get_nowait()
            except queue.Empty:
                break

            action = item[0]
            if action == 'popup':
                _, source_text, translated_text = item
                self.show_translation_popup(source_text, translated_text)
            elif action == 'stop':
                should_stop = True

        if should_stop:
            self.destroy_ui()
            return

        if self.root is not None and not self.stop_event.is_set():
            self.root.after(100, self.process_ui_queue)

    def queue_translation_popup(self, source_text, translated_text):
        """把弹窗任务交给 UI 主线程。"""
        if self.root is None:
            self.show_notification("英文翻译", translated_text[:100])
            return

        self.ui_queue.put(('popup', source_text, translated_text))

    def draw_rounded_rect(self, canvas, x1, y1, x2, y2, radius, **kwargs):
        """在 Canvas 上绘制圆角矩形。"""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def fade_in_popup(self, popup, target_alpha=1.0, current_alpha=0.0):
        """轻量淡入，让弹窗出现不那么突兀。"""
        if not popup.winfo_exists():
            return

        next_alpha = min(target_alpha, current_alpha + 0.14)
        try:
            popup.attributes('-alpha', next_alpha)
        except tk.TclError:
            return

        if next_alpha < target_alpha:
            popup.after(16, lambda: self.fade_in_popup(popup, target_alpha, next_alpha))

    def show_translation_popup(self, source_text, translated_text):
        """显示英文自动翻译结果小窗口。"""
        if self.root is None:
            return

        try:
            if self.current_popup is not None and self.current_popup.winfo_exists():
                self.current_popup.destroy()
        except tk.TclError:
            pass

        popup = tk.Toplevel(self.root)
        self.current_popup = popup
        popup.title("英文翻译")
        popup.overrideredirect(True)
        popup.attributes('-topmost', True)
        popup.resizable(False, False)
        try:
            popup.attributes('-alpha', 0.0)
        except tk.TclError:
            pass

        transparent_color = '#ff00ff'
        popup.configure(bg=transparent_color)
        try:
            popup.wm_attributes('-transparentcolor', transparent_color)
        except tk.TclError:
            transparent_color = '#e5e7eb'
            popup.configure(bg=transparent_color)

        width = 720
        height = 520
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = max(screen_width - width - 32, 0)
        y = max(screen_height - height - 80, 0)
        popup.geometry(f"{width}x{height}+{x}+{y}")

        canvas = tk.Canvas(
            popup,
            width=width,
            height=height,
            bg=transparent_color,
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(fill='both', expand=True)

        self.draw_rounded_rect(canvas, 16, 18, width - 8, height - 8, 10, fill='#cbd5e1', outline='')
        self.draw_rounded_rect(canvas, 12, 13, width - 12, height - 12, 10, fill='#e2e8f0', outline='')
        self.draw_rounded_rect(canvas, 10, 8, width - 16, height - 18, 8, fill='#ffffff', outline='#d9e2ef')

        content = tk.Frame(canvas, bg='#ffffff')
        canvas.create_window(22, 18, anchor='nw', width=width - 60, height=height - 62, window=content)

        header = tk.Frame(content, bg='#ffffff', height=46)
        header.pack(fill='x')
        header.pack_propagate(False)

        mark = tk.Canvas(header, width=32, height=32, bg='#ffffff', highlightthickness=0, bd=0)
        mark.pack(side='left', pady=(3, 0))
        self.draw_rounded_rect(mark, 1, 1, 31, 31, 8, fill='#eef2ff', outline='#c7d2fe')
        mark.create_text(16, 16, text='译', fill='#3730a3', font=('Microsoft YaHei UI', 10, 'bold'))

        title_block = tk.Frame(header, bg='#ffffff')
        title_block.pack(side='left', fill='both', expand=True, padx=(9, 0))

        title = tk.Label(
            title_block,
            text="英文自动翻译",
            bg='#ffffff',
            fg='#111827',
            font=('Microsoft YaHei UI', 11, 'bold'),
            anchor='w'
        )
        title.pack(fill='x')

        meta = tk.Label(
            title_block,
            text="EN -> 中文",
            bg='#ffffff',
            fg='#6b7280',
            font=('Microsoft YaHei UI', 8),
            anchor='w'
        )
        meta.pack(fill='x', pady=(2, 0))

        close_header = tk.Button(
            header,
            text='×',
            command=popup.destroy,
            bg='#ffffff',
            fg='#64748b',
            activebackground='#f1f5f9',
            activeforeground='#111827',
            relief='flat',
            borderwidth=0,
            font=('Segoe UI', 15),
            width=3,
            cursor='hand2'
        )
        close_header.pack(side='right', pady=(2, 0))

        source_preview = source_text[:180] + ('...' if len(source_text) > 180 else '')
        source_card = tk.Frame(content, bg='#f8fafc', highlightbackground='#e2e8f0', highlightthickness=1)
        source_card.pack(fill='x', pady=(6, 10))
        source_card.configure(height=58)
        source_card.pack_propagate(False)

        source_label = tk.Label(
            source_card,
            text=source_preview,
            bg='#f8fafc',
            fg='#64748b',
            justify='left',
            anchor='w',
            wraplength=620,
            font=('Microsoft YaHei UI', 9),
            padx=10,
            pady=8
        )
        source_label.pack(fill='x')

        result_header = tk.Frame(content, bg='#ffffff')
        result_header.pack(fill='x', pady=(0, 6))

        result_title = tk.Label(
            result_header,
            text="译文",
            bg='#ffffff',
            fg='#111827',
            font=('Microsoft YaHei UI', 9, 'bold'),
            anchor='w'
        )
        result_title.pack(side='left')

        hint = tk.Label(
            result_header,
            text="Esc 关闭",
            bg='#ffffff',
            fg='#94a3b8',
            font=('Microsoft YaHei UI', 8),
            anchor='e'
        )
        hint.pack(side='right')

        button_row = tk.Frame(content, bg='#ffffff')
        button_row.pack(side='bottom', fill='x', pady=(13, 0))

        status_label = tk.Label(
            button_row,
            text=f"原文 {len(source_text)} 字符 | 译文 {len(translated_text)} 字符",
            bg='#ffffff',
            fg='#94a3b8',
            font=('Microsoft YaHei UI', 8)
        )
        status_label.pack(side='left', pady=(7, 0))

        result_card = tk.Frame(content, bg='#dbe4f0')
        result_card.pack(fill='both', expand=True)

        result_box = tk.Text(
            result_card,
            height=14,
            wrap='word',
            relief='flat',
            borderwidth=0,
            bg='#f8fafc',
            fg='#0f172a',
            padx=12,
            pady=10,
            font=('Microsoft YaHei UI', 11),
            spacing1=2,
            spacing2=1,
            spacing3=3,
            insertbackground='#2563eb',
            selectbackground='#bfdbfe'
        )
        result_box.insert('1.0', translated_text)
        result_box.configure(state='disabled')
        result_box.pack(side='left', fill='both', expand=True, padx=(1, 0), pady=1)

        scrollbar = ttk.Scrollbar(result_card, command=result_box.yview)
        scrollbar.pack(side='right', fill='y', pady=1, padx=(0, 1))
        result_box.configure(yscrollcommand=scrollbar.set)

        def copy_translation():
            pyperclip.copy(translated_text)
            self.remember_ignored_clipboard_text(translated_text)
            copy_button.configure(text="已复制", bg='#16a34a', activebackground='#15803d')

        close_button = tk.Button(
            button_row,
            text="关闭",
            command=popup.destroy,
            bg='#f1f5f9',
            fg='#334155',
            activebackground='#e2e8f0',
            activeforeground='#0f172a',
            relief='flat',
            borderwidth=0,
            padx=16,
            pady=8,
            font=('Microsoft YaHei UI', 9),
            cursor='hand2'
        )
        close_button.pack(side='right', padx=(8, 0))

        copy_button = tk.Button(
            button_row,
            text="复制译文",
            command=copy_translation,
            bg='#2563eb',
            fg='#ffffff',
            activebackground='#1d4ed8',
            activeforeground='#ffffff',
            relief='flat',
            borderwidth=0,
            padx=18,
            pady=8,
            font=('Microsoft YaHei UI', 9, 'bold'),
            cursor='hand2'
        )
        copy_button.pack(side='right')

        def start_move(event):
            popup._drag_start_x = event.x_root - popup.winfo_x()
            popup._drag_start_y = event.y_root - popup.winfo_y()

        def move_popup(event):
            popup.geometry(
                f"+{event.x_root - popup._drag_start_x}"
                f"+{event.y_root - popup._drag_start_y}"
            )

        for drag_widget in (header, title_block, title, meta, mark):
            drag_widget.bind('<ButtonPress-1>', start_move)
            drag_widget.bind('<B1-Motion>', move_popup)

        popup.bind('<Escape>', lambda event: popup.destroy())

        popup_seconds = int(self.auto_translate.get('popup_seconds', 0))
        if popup_seconds > 0:
            popup.after(popup_seconds * 1000, lambda: popup.winfo_exists() and popup.destroy())

        self.fade_in_popup(popup)

    def destroy_ui(self):
        """关闭 tkinter UI。"""
        if self.root is None:
            return

        try:
            self.root.quit()
            self.root.destroy()
        except tk.TclError:
            pass

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
        self.setup_ui()

        print("翻译助手已启动！")
        print("使用方法：")
        print(f"1. 复制中文文本 (Ctrl+C)，按 {self.clipboard_hotkey.upper()} 翻译剪贴板")
        print(f"2. 选中文本，按鼠标上侧键自动复制并翻译")
        print("3. 复制英文文本时自动弹窗翻译")
        print("4. 翻译结果自动复制到剪贴板")
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

        self.start_auto_clipboard_monitor()

        # 保持程序运行
        if self.root is not None:
            self.root.mainloop()
        else:
            keyboard.wait()

    def stop(self):
        """停止程序"""
        if self.stop_event.is_set():
            return

        print("\n翻译助手已退出")
        self.stop_event.set()
        keyboard.unhook_all()
        if mouse is not None:
            mouse.unhook_all()

        if self.root is not None:
            self.ui_queue.put(('stop',))
        else:
            os._exit(0)


if __name__ == '__main__':
    app = TranslationHotkey()
    app.start()
