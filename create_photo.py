# create_photo.py

from http import HTTPStatus
import requests
from dashscope import ImageSynthesis
import os
import logging
import sys


def setup_logging():
    # 确保log目录存在
    if not os.path.exists('log'):
        os.makedirs('log')

    logger = logging.getLogger('image_generation')
    logger.setLevel(logging.INFO)

    logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler('log/image_generation.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


photo_logger = setup_logging()

class Create_photo:
    def __init__(self, api_key, file_name='123.jpg'):
        """
        初始化Create_photo类

        Args:
            api_key (str): DashScope API密钥
            file_name (str): 图片保存文件名，默认为'123.jpg'
        """
        self.api_key = api_key
        self.model = "wan2.2-t2i-flash" # 注意：模型名可能需要确认
        self.file_name = file_name

    def create(self, prompt):
        # 优化提示词构建
        full_prompt = f'''
        以下是一个文章的相关信息，包括题目、链接、期刊、以及摘要，请帮我生成一张相关插画；
        要求符合伦理，不能出现让人反胃的画面，要符合论文主题，论文具体内容为{prompt}。
        '''

        photo_logger.info(f"开始生成图片，提示词长度: {len(full_prompt)}")

        try:
            # 调用图像生成API
            rsp = ImageSynthesis.call(
                api_key=self.api_key,
                model=self.model,
                prompt=full_prompt,
                n=1,           # 请求生成1张图片
                size='1440*1080' # 指定图片尺寸
            )

            # 打印完整的响应对象用于调试
            photo_logger.debug(f"DashScope API 响应对象: {rsp}")

            # 检查API调用的整体状态
            if rsp.status_code == HTTPStatus.OK:
                photo_logger.info("API调用成功")

                # *** 关键修改：增加健壮性检查 ***
                # 1. 检查 rsp.output 是否存在
                if not hasattr(rsp, 'output') or rsp.output is None:
                    photo_logger.error("API响应中缺少 'output' 字段")
                    return None

                # 2. 检查 rsp.output.results 是否存在且为列表
                if not hasattr(rsp.output, 'results') or not isinstance(rsp.output.results, list):
                     photo_logger.error("'output.results' 不存在或不是列表")
                     return None

                # 3. 检查 results 列表是否为空
                if len(rsp.output.results) == 0:
                    photo_logger.error("'output.results' 列表为空，未生成任何图片")
                    # 尝试打印 reason 或 message 获取更多信息
                    reason = getattr(rsp.output, 'message', '无具体原因')
                    photo_logger.error(f"API输出消息: {reason}")
                    return None

                # 4. 获取第一个结果
                first_result = rsp.output.results[0]

                # 5. 检查第一个结果是否有 'url' 属性
                if not hasattr(first_result, 'url') or not first_result.url:
                     photo_logger.error("第一个结果中缺少 'url' 属性或URL为空")
                     return None

                # 如果所有检查都通过，则获取URL
                image_url = first_result.url
                photo_logger.info(f"成功获取到图片URL: {image_url}")
                # *** 修改结束 ***

                # 下载并保存图片
                try:
                    response = requests.get(image_url, timeout=30) # 添加超时
                    response.raise_for_status() # 如果HTTP请求返回了不成功的状态码，抛出异常

                    # 确保 dynamic_images 目录存在 (如果需要的话)
                    # os.makedirs(os.path.dirname(self.file_name), exist_ok=True)

                    with open(self.file_name, 'wb') as f:
                        f.write(response.content)

                    photo_logger.info(f"图片已成功保存到: {self.file_name}")
                    return self.file_name

                except requests.exceptions.RequestException as e:
                    photo_logger.error(f"下载图片失败: {e}")
                    return None

            else:
                # API调用失败，记录状态码和错误信息
                status_code = getattr(rsp, 'status_code', 'N/A')
                error_message = getattr(rsp, 'message', '未知错误')
                request_id = getattr(rsp, 'request_id', 'N/A')
                photo_logger.error(f"图片生成失败 - 状态码: {status_code}, 错误信息: {error_message}, Request ID: {request_id}")
                return None

        except Exception as e:
            # 捕获所有其他未预期的异常
            photo_logger.error(f'图片生成过程中发生未预期异常: {e}', exc_info=True) # exc_info=True 打印堆栈跟踪
            return None


if __name__ == "__main__":
    # 测试代码
    photo_creator = Create_photo(api_key='key', file_name='dynamic_images\\ai_40794953.jpg')

    # 使用一个更具体的测试提示词
    test_prompt = "一间有着精致窗户的花店，漂亮的木质门，摆放着各种美丽的花朵，阳光明媚，色彩鲜艳，卡通风格"
    file_path = photo_creator.create(test_prompt)

    if file_path:
        print(f'>>> 成功: 图片已保存到: {file_path}')
        photo_logger.info("程序执行完成，图片生成成功")
    else:
        print('>>> 失败: 图片生成失败')
        photo_logger.info("程序执行完成，图片生成失败")
