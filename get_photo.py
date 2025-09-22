import requests
import time
import os
import logging
import sys

def setup_logging():
    # 确保log目录存在
    if not os.path.exists('log'):
        os.makedirs('log')

    logger = logging.getLogger('get_photo')
    logger.setLevel(logging.INFO)

    logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler('log/get_photo.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


get_photo_logger = setup_logging()


def get_screenshot_local(url, api_key, output_file="image/screenshot.ipg"):
    get_photo_logger.info(f"开始处理截图请求 - URL: {url}")

    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        get_photo_logger.info(f"创建输出目录: {output_dir}")

    scan_url = "https://urlscan.io/api/v1/scan/"
    headers = {
        'API-Key': api_key.strip(),
        'Content-Type': 'application/json'
    }

    data = {
        'url': url.strip(),
        'visibility': 'public'
    }

    try:
        get_photo_logger.info("提交扫描请求到 urlscan.io")

        response = requests.post(scan_url, headers=headers, json=data, timeout=30)

        if response.status_code == 200:
            result = response.json()
            scan_id = result.get('uuid')
            get_photo_logger.info(f"扫描已提交成功，ID: {scan_id}")

            # 等待扫描完成
            get_photo_logger.info("等待截图生成... (15秒)")
            time.sleep(15)

            # 构建截图URL
            screenshot_url = f"https://urlscan.io/screenshots/{scan_id}.png"
            get_photo_logger.info(f"构建截图URL: {screenshot_url}")

            get_photo_logger.info("正在下载截图...")
            screenshot_response = requests.get(screenshot_url, timeout=30)

            if screenshot_response.status_code == 200:
                with open(output_file, 'wb') as f:
                    f.write(screenshot_response.content)
                get_photo_logger.info(f"截图已成功保存为: {output_file}")
                return output_file
            else:
                error_msg = f"下载截图失败: HTTP {screenshot_response.status_code}"
                get_photo_logger.error(error_msg)
                return error_msg
        else:
            error_msg = f"扫描请求失败: HTTP {response.status_code} - {response.text}"
            get_photo_logger.error(error_msg)
            return error_msg
    except requests.exceptions.Timeout:
        error_msg = "请求超时"
        get_photo_logger.error(error_msg)
        return error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"网络请求异常: {str(e)}"
        get_photo_logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"未知异常: {str(e)}"
        get_photo_logger.error(error_msg)
        return error_msg


if __name__ == "__main__":
    get_photo_logger.info("=== 截图应用启动 ===")

    API_KEY = "key"  # 替换为您的API Key
    website_url = "https://pubmed.ncbi.nlm.nih.gov/32594390/"

    get_photo_logger.info(f"目标URL: {website_url}")
    get_photo_logger.info(f"使用API Key: {API_KEY[:8]}...")  # 只记录部分API Key用于识别

    result = get_screenshot_local(website_url, API_KEY, "image/pubmed_screenshot.ipg")
    get_photo_logger.info(f"执行结果: {result}")

    get_photo_logger.info("=== 截图应用执行完成 ===")