# 该模块主要封装了通过API进行问题回答的类
from openai import OpenAI
import json
import requests

API_KEY = 'your_key'

class AnswerAPI:
    # 阿里云模型广场连接
    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # 模型选取
    ASK_MODEL_ONE = "qwen-max"
    ASK_MODEL_TWO = "deepseek-v3"

    def __init__(self, api_key):

        self.api_key = api_key
        self.client = OpenAI(api_key=self.api_key, base_url=self.BASE_URL)

    def for_answer_one(self, prompt):
        messages = [
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ]

        completion = self.client.chat.completions.create(
            model=self.ASK_MODEL_ONE,
            messages=messages
        )

        response = completion.model_dump_json()
        response = json.loads(response)
        answer = response.get('choices')[0].get('message').get('content')

        return answer

    def for_answer_two(self, prompt):
        completion = self.client.chat.completions.create(
            model=self.ASK_MODEL_TWO,
            messages=[
                {'role': 'user', 'content': prompt}
            ]
        )

        answer = completion.choices[0].message.content
        return answer