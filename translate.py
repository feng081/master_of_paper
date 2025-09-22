import requests
import hashlib
import re
import os
import logging


APPID = "appid"
KEY = "key"
API_URL = "url"  # 翻译API


log_dir = 'log'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

def setup_logger():
    logger = logging.getLogger('baidu_translator')
    logger.setLevel(logging.INFO)

    if logger.handlers:
        logger.handlers.clear()

    file_handler = logging.FileHandler(
        filename=os.path.join(log_dir, 'translation.log'),
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

logger = setup_logger()

def contains_chinese(text):
    """判断文本是否包含中文字符"""
    if not text or not isinstance(text, str):
        return False
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def baidu_translate_if_chinese(text, target_lang="en"):
    """
    如果文本包含中文，则翻译成目标语言（如英文）；否则返回原文。
    :param text: 要翻译的文本
    :param target_lang: 目标语言，如 'en'
    :return: 翻译后的文本 或 原文
    """
    if not text or not str(text).strip():
        clean_text = str(text) if text is not None else ""
        logger.info(f"输入为空，返回: '{clean_text}'")
        return clean_text

    text = str(text).strip()

    if not contains_chinese(text):
        logger.info(f"跳过翻译（非中文）: '{text}'")
        return text

    logger.info(f"正在翻译中文: '{text}'")

    salt = "123456"
    sign_str = APPID + text + salt + KEY
    sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()

    params = {
        'q': text,
        'from': 'auto',
        'to': target_lang,
        'appid': APPID,
        'salt': salt,
        'sign': sign
    }

    try:
        response = requests.get(API_URL, params=params, timeout=10)
        result = response.json()

        if 'trans_result' in result and len(result['trans_result']) > 0:
            translated = result['trans_result'][0]['dst']
            logger.info(f"翻译成功: '{translated}'")
            return translated
        else:
            error_msg = result.get('error_msg', 'Unknown error')
            logger.error(f"翻译失败: {error_msg} | 原文: '{text}'")
            return f"[翻译失败] {text}"

    except Exception as e:
        logger.exception(f"请求异常: {e} | 原文: '{text}'")  # 使用 exception 输出完整 traceback
        return f"[错误] {text}"

if __name__ == "__main__":
    test_texts = [
        "你好，世界",
        "This is an English sentence.",
        "肺癌的早期症状",
        "No translation needed here.",
        "",
    ]

    for text in test_texts:
        result = baidu_translate_if_chinese(text, target_lang="en")
        print(f"原文: {repr(text)} → 结果: {repr(result)}\n")