import hashlib
import random
import json
import requests
from pathlib import Path


class BaiduTranslator:
    def __init__(self, config_path='config.json'):
        """初始化翻译器，加载配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.app_id = config['baidu']['app_id']
        self.secret_key = config['baidu']['secret_key']
        self.from_lang = config['translation']['from_lang']
        self.to_lang = config['translation']['to_lang']
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
            response = requests.get(self.api_url, params=params, timeout=5)
            result = response.json()

            if 'trans_result' in result:
                translated_text = '\n'.join([item['dst'] for item in result['trans_result']])
                return translated_text
            else:
                error_msg = result.get('error_msg', '未知错误')
                return f"翻译失败: {error_msg}"

        except Exception as e:
            return f"翻译出错: {str(e)}"


if __name__ == '__main__':
    # 测试代码
    translator = BaiduTranslator()
    test_text = "你好，世界"
    result = translator.translate(test_text)
    print(f"原文: {test_text}")
    print(f"译文: {result}")
