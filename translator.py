import hashlib
import random
import json
import requests
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

    def translate(self, text):
        """翻译文本"""
        if not text.strip():
            return ""

        # 生成随机数
        salt = str(random.randint(32768, 65536))

        # 生成签名
        sign_str = self.app_id + text + salt + self.secret_key
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()

        # 请求参数
        params = {
            'q': text,
            'from': self.from_lang,
            'to': self.to_lang,
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


if __name__ == '__main__':
    # 测试代码
    translator = BaiduTranslator()
    test_text = "你好，世界"
    result = translator.translate(test_text)
    print(f"原文: {test_text}")
    print(f"译文: {result}")
