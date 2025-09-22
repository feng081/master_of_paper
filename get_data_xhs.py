# -*- coding: utf-8 -*-
import logging

qa_logger = logging.getLogger('log/question_answerer')
qa_logger.setLevel(logging.INFO)

# 避免重复添加 handler
if not qa_logger.handlers:
    # 创建文件 handler 并设置编码为 UTF-8
    file_handler = logging.FileHandler('log/question_answerer.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # 创建控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 创建 formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 设置 formatter
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 添加 handlers 到 logger
    qa_logger.addHandler(file_handler)
    qa_logger.addHandler(console_handler)


class QuestionAnswerer:
    """
    一个封装了通过API进行问题回答的类。
    """

    def __init__(self, api_key, model_name="deepseek-v3"):
        """
        初始化 QuestionAnswerer 实例。
        """
        qa_logger.info(f"初始化 QuestionAnswerer 实例, 使用模型: {model_name}")
        try:
            from for_answer import AnswerAPI
            self.answer_api = AnswerAPI(api_key=api_key)
            self.model_name = model_name
            qa_logger.info("AnswerAPI 实例化成功")
        except ImportError as e:
            error_msg = f"无法导入 AnswerAPI 类: {e}. 请检查 'for_answer' 模块是否存在且可访问。"
            qa_logger.error(error_msg)
            raise ImportError(error_msg) from e
        except Exception as e: # 捕获实例化 AnswerAPI 时可能出现的其他错误
            error_msg = f"实例化 AnswerAPI 时出错: {e}"
            qa_logger.error(error_msg)
            raise

    def ask(self, prompt):

        all_prompt = f'''
        一篇论文的详细信息为{prompt}；
        请帮我对改论文进行总结，具体格式要求如下：
        以往的研究表明，人工智能（AI）在心理治疗中的应用引起了广泛关注。然而，关于AI生成的回应与人类治疗师的回应在质量和可辨识性方面的差异，尚缺乏深入研究。
        一项最新的研究探讨了ChatGPT在夫妻治疗情境中的表现。研究人员设计了18个夫妻治疗场景，分别由人类治疗师和ChatGPT生成回应。然后，招募了800多名参与者，对这些回应进行评估，判断其来源并评分。
        结果显示，参与者难以区分哪些回应来自ChatGPT，哪些来自人类治疗师。此外，ChatGPT生成的回应获得的评分普遍高于人类治疗师的回应。进一步分析发现，ChatGPT的回应通常更长，包含更多的名词和形容词，提供了更丰富的上下文信息，这可能是其获得更高评分的原因之一。
        这项研究表明，ChatGPT在心理治疗中具有潜在的应用价值。然而，作者强调，尽管AI显示出积极的前景，但在将其整合到心理健康护理中时，需要谨慎考虑伦理和实践方面的问题。专业人士应积极参与AI的发展，以确保其在受监督和负责任的环境中应用，从而提高护理质量和可及性。不过尽管如此，人不是机器，会更倾向于面对面的交流和共情，这一点也许AI永远都无法取代。
        根据论文具体内容进行回答，不要进行联想，论文种没有提到的，不要出现，不要出现“可能”！！可以根据具体的内容多添加一些小表情，针对研究方法部分可以再具体一些，主要发现的内容也多一些，多点娱乐性的话术，只输出上述提到的内容，不要输出别的内容！！！不要抄写上面的内容！！！
        '''
        qa_logger.info(f"收到 ask 请求, 模型: {self.model_name}, Prompt 长度: {len(all_prompt) if all_prompt else 0}")

        if not isinstance(all_prompt, str) or not all_prompt.strip():
            error_msg = "all_prompt 必须是非空字符串。"
            qa_logger.warning(error_msg)
            raise ValueError(error_msg)

        try:
            method_name = "for_answer_two" if self.model_name == "deepseek-v3" else "for_answer_one"
            qa_logger.debug(f"调用 AnswerAPI.{method_name} 方法")

            if self.model_name == "deepseek-v3":
                answer = self.answer_api.for_answer_two(all_prompt)
            elif self.model_name == "qwen3-30b-a3b":
                answer = self.answer_api.for_answer_one(all_prompt)
            else:
                error_msg = f"不支持的模型名称: {self.model_name}。支持的模型: 'deepseek-v3', 'qwen3-30b-a3b'"
                qa_logger.error(error_msg)
                raise ValueError(error_msg)

            qa_logger.info(f"成功获取回答, 回答长度: {len(answer) if answer else 0}")

            return answer

        except Exception as e:
            # 记录详细的错误信息
            error_msg = f"调用API生成回答时出错: {e}"
            qa_logger.error(error_msg, exc_info=True) # exc_info=True 会记录完整的堆栈跟踪
            # 重新抛出异常，让调用者处理
            raise Exception(error_msg) from e

if __name__ == '__main__':
    YOUR_API_KEY = 'key'

    # 1. 使用默认的 deepseek-v3 模型
    print("--- 使用 deepseek-v3 模型 ---")
    qa_agent_v3 = QuestionAnswerer(api_key=YOUR_API_KEY, model_name="deepseek-v3")

    prompt1 = "请用一句话解释量子计算。"
    try:
        answer1 = qa_agent_v3.ask(prompt1)
        print(f"Prompt: {prompt1}")
        print(f"Answer: {answer1}\n")
    except Exception as e:
        print(f"获取回答失败: {e}\n")

    # 2. 使用 qwen3-30b-a3b 模型
    print("--- 使用 qwen3-30b-a3b 模型 ---")
    qa_agent_qwen = QuestionAnswerer(api_key=YOUR_API_KEY, model_name="qwen3-30b-a3b")

    prompt2 = "期刊‘Expert review of proteomics’的影响因子为多少？要求只输出影响因子，不要有任何额外的输出，只需要一个准确的数字"
    try:
        answer2 = qa_agent_qwen.ask(prompt2)
        print(f"Prompt: {prompt2}")
        print(f"Answer: {answer2}\n")
    except Exception as e:
        print(f"获取回答失败: {e}\n")

    # 3. 测试错误处理
    print("--- 测试错误处理 ---")
    try:
        # 尝试使用不支持的模型
        qa_agent_invalid = QuestionAnswerer(api_key=YOUR_API_KEY, model_name="invalid-model")
        qa_agent_invalid.ask("测试问题")
    except ValueError as e:
        print(f"捕获到预期的 ValueError: {e}")

    try:
        # 尝试传入空prompt
        qa_agent_v3.ask("")
    except ValueError as e:
        print(f"捕获到预期的 ValueError: {e}")

