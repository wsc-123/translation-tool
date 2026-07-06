import hashlib
import random
import json
import requests
import re
import time
from pathlib import Path


class ConfigError(RuntimeError):
    """Raised when the local configuration file is missing or invalid."""


class BaiduTranslator:
    def __init__(self, config_path='config.json'):
        """初始化翻译器，加载配置"""
        self.config_path = Path(config_path)
        if not self.config_path.is_absolute():
            self.config_path = Path(__file__).resolve().with_name(config_path)

        if not self.config_path.exists():
            raise ConfigError(
                "未找到 config.json。请先复制 config.example.json 为 config.json，"
                "并填写你的百度翻译 APP ID 和密钥。"
            )

        try:
            with self.config_path.open('r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"config.json 格式错误: {exc}") from exc

        try:
            self.app_id = config['baidu']['app_id']
            self.secret_key = config['baidu']['secret_key']
            self.from_lang = config['translation']['from_lang']
            self.to_lang = config['translation']['to_lang']
        except KeyError as exc:
            raise ConfigError(f"config.json 缺少配置项: {exc}") from exc

        if not self.app_id or not self.secret_key:
            raise ConfigError("请在 config.json 中填写有效的百度翻译 APP ID 和密钥。")

        self.api_url = 'https://fanyi-api.baidu.com/api/trans/vip/translate'
        self.max_chunk_chars = 1400
        self.chunk_delay = 1.1

    def translate(self, text, from_lang=None, to_lang=None):
        """翻译文本"""
        if not text.strip():
            return ""

        source_lang = from_lang or self.from_lang
        target_lang = to_lang or self.to_lang
        chunks = self.split_text(text, self.max_chunk_chars)

        if len(chunks) == 1:
            return self.translate_chunk(chunks[0], source_lang, target_lang)

        translated_chunks = []
        for index, chunk in enumerate(chunks):
            if index > 0:
                time.sleep(self.chunk_delay)

            translated = self.translate_chunk(chunk, source_lang, target_lang)
            if translated.startswith(("翻译失败", "翻译出错")):
                return translated

            translated_chunks.append(translated)

        return '\n'.join(translated_chunks)

    def translate_chunk(self, text, source_lang, target_lang):
        """翻译单个短文本块。"""

        # 生成随机数
        salt = str(random.randint(32768, 65536))

        # 生成签名
        sign_str = self.app_id + text + salt + self.secret_key
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()

        # 请求参数
        params = {
            'q': text,
            'from': source_lang,
            'to': target_lang,
            'appid': self.app_id,
            'salt': salt,
            'sign': sign
        }

        try:
            response = requests.post(self.api_url, data=params, timeout=10)
            response.raise_for_status()
            result = response.json()

            if 'trans_result' in result:
                translated_text = '\n'.join([item['dst'] for item in result['trans_result']])
                return translated_text
            else:
                error_code = result.get('error_code', 'unknown')
                error_msg = result.get('error_msg', '未知错误')
                return f"翻译失败({error_code}): {error_msg}"

        except Exception as e:
            return f"翻译出错: {str(e)}"

    def split_text(self, text, max_chars):
        """把长文本切成适合 API 请求的块。"""
        normalized = text.replace('\r\n', '\n').replace('\r', '\n').strip()
        if len(normalized) <= max_chars:
            return [normalized]

        pieces = []
        for paragraph in normalized.split('\n'):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            pieces.extend(self.split_paragraph(paragraph, max_chars))

        chunks = []
        current = ""
        for piece in pieces:
            separator = "\n" if current else ""
            if len(current) + len(separator) + len(piece) <= max_chars:
                current = f"{current}{separator}{piece}"
            else:
                if current:
                    chunks.append(current)
                current = piece

        if current:
            chunks.append(current)

        return chunks

    def split_paragraph(self, paragraph, max_chars):
        """按句子和单词拆分段落。"""
        if len(paragraph) <= max_chars:
            return [paragraph]

        sentences = re.split(r'(?<=[.!?。！？])\s+', paragraph)
        pieces = []
        current = ""

        for sentence in sentences:
            if len(sentence) > max_chars:
                if current:
                    pieces.append(current)
                    current = ""
                pieces.extend(self.split_long_sentence(sentence, max_chars))
                continue

            separator = " " if current else ""
            if len(current) + len(separator) + len(sentence) <= max_chars:
                current = f"{current}{separator}{sentence}"
            else:
                pieces.append(current)
                current = sentence

        if current:
            pieces.append(current)

        return pieces

    def split_long_sentence(self, sentence, max_chars):
        """拆分超长句子，优先按单词边界切。"""
        words = sentence.split()
        if len(words) <= 1:
            return [sentence[i:i + max_chars] for i in range(0, len(sentence), max_chars)]

        pieces = []
        current = ""
        for word in words:
            if len(word) > max_chars:
                if current:
                    pieces.append(current)
                    current = ""
                pieces.extend(word[i:i + max_chars] for i in range(0, len(word), max_chars))
                continue

            separator = " " if current else ""
            if len(current) + len(separator) + len(word) <= max_chars:
                current = f"{current}{separator}{word}"
            else:
                if current:
                    pieces.append(current)
                current = word

        if current:
            pieces.append(current)

        return pieces


if __name__ == '__main__':
    # 测试代码
    translator = BaiduTranslator()
    test_text = "你好，世界"
    result = translator.translate(test_text)
    print(f"原文: {test_text}")
    print(f"译文: {result}")
