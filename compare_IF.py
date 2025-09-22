# compare_IF.py

import pandas as pd
import logging
from for_answer import AnswerAPI
import time

logger = logging.getLogger('log/paper_ranker')
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler('log/paper_ranker.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


class PaperRankerByIF:

    def __init__(self, df, journal_column_name='期刊', api_key=None):
        logger.info("初始化 PaperRankerByIF 实例")
        if not isinstance(df, pd.DataFrame):
            error_msg = "输入必须是一个 pandas DataFrame 对象。"
            logger.error(error_msg)
            raise TypeError(error_msg)

        # 保存原始数据框的副本
        self.df_with_if = df.copy()
        self.journal_col = journal_column_name
        self.if_col = '影响因子'
        self.api_key = api_key

        if self.journal_col not in self.df_with_if.columns:
            error_msg = f"DataFrame 中未找到名为 '{self.journal_col}' 的列。"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 初始化影响因子列为 None
        self.df_with_if[self.if_col] = None
        logger.info(f"PaperRankerByIF 实例初始化完成。数据集包含 {len(self.df_with_if)} 行。")

    def get_impact_factor(self, journal_name):
        logger.info(f"开始获取期刊 '{journal_name}' 的影响因子")
        if not journal_name or not isinstance(journal_name, str):
            warning_msg = f"无效的期刊名称: {journal_name}"
            logger.warning(warning_msg)
            return None

        journal_name_clean = journal_name.strip()
        if not journal_name_clean:
            warning_msg = "期刊名称为空"
            logger.warning(warning_msg)
            return None

        try:
            prompt_one = f'''
            期刊‘{journal_name_clean}’的影响因子为多少？
            要求只输出影响因子，不要有任何额外的输出，只需要一个准确的数字
            '''
            logger.debug(f"API 请求 Prompt: {prompt_one}")

            ask = AnswerAPI(self.api_key)
            response_text = ask.for_answer_two(prompt_one)
            logger.debug(f"API 响应原始文本: '{response_text}'")

            if response_text and "无法获取" not in response_text:
                response_text = response_text.strip()
                # 尝试转换为浮点数
                impact_factor = float(response_text)
                success_msg = f"成功获取 '{journal_name_clean}' 的IF: {impact_factor}"
                logger.info(success_msg)
                return impact_factor
            else:
                warning_msg = f"API未能返回有效IF for '{journal_name_clean}', 返回: '{response_text}'"
                logger.warning(warning_msg)
                return None

        except ValueError as e:
            # 如果转换失败，记录日志并返回 None
            error_msg = f"转换API返回值 '{response_text}' 为数字时出错 for '{journal_name_clean}': {e}"
            logger.error(error_msg)
            return None
        except Exception as e:
            # 捕获API调用过程中可能出现的其他异常
            error_msg = f"调用API获取 '{journal_name_clean}' 的IF时发生未知错误: {e}"
            logger.error(error_msg)
            return None

    def fetch_all_if(self):
        """
        遍历DataFrame中的所有唯一期刊名，调用API获取IF，并填充到DataFrame中。
        """
        logger.info("开始获取所有期刊的影响因子...")
        # 获取唯一且非空的期刊名称以减少API调用次数
        # 确保期刊名列是字符串类型，处理可能的非字符串类型（如 float nan）
        unique_journals = self.df_with_if[self.journal_col].dropna().astype(str).unique()
        # 过滤掉 'nan' 字符串（如果astype(str)将np.nan转为了'nan'）
        unique_journals = [j for j in unique_journals if j.lower() != 'nan']
        logger.info(f"需要查询 {len(unique_journals)} 个唯一期刊的IF: {unique_journals}")

        journal_if_map = {}
        for journal_name in unique_journals:
            journal_name_clean = journal_name.strip()
            if journal_name_clean:  # 确保名称非空
                logger.info(f"正在处理期刊: {journal_name_clean}")
                if_value = self.get_impact_factor(journal_name_clean)
                journal_if_map[journal_name_clean] = if_value
                logger.info(f"期刊 '{journal_name_clean}' 的IF已记录: {if_value}")
                # 在API调用间添加延迟，避免请求过于频繁
                time.sleep(0.5)

        logger.info("API调用阶段完成，开始将IF映射到DataFrame...")
        # 将映射应用到DataFrame
        # 注意：这里假设期刊名列中的值与journal_if_map的键格式一致
        self.df_with_if[self.if_col] = self.df_with_if[self.journal_col].astype(str).map(journal_if_map)
        # 将无法匹配或原始为NaN的IF值设回NaN
        self.df_with_if.loc[self.df_with_if[self.journal_col].isna() | (
                    self.df_with_if[self.journal_col].astype(str).str.lower() == 'nan'), self.if_col] = None

        logger.info("所有期刊影响因子获取并映射完成。")

    def get_top_papers(self, top_n=10):
        """
        根据获取到的影响因子，对所有论文进行排序，并返回IF最高的前 top_n 篇论文。
        """
        logger.info(f"开始查找IF最高的前 {top_n} 篇论文...")

        # 检查是否需要获取IF
        # 如果影响因子列不存在或全为NaN，则需要获取
        if self.if_col not in self.df_with_if.columns or self.df_with_if[self.if_col].isna().all():
            logger.info("检测到影响因子未获取或全为空，正在获取...")
            self.fetch_all_if()
        else:
            logger.info("影响因子已存在，跳过获取步骤。")

        logger.info("开始处理IF数据类型...")
        # 确保IF列是数值类型，以便正确排序
        self.df_with_if[self.if_col] = pd.to_numeric(self.df_with_if[self.if_col], errors='coerce')
        logger.info("IF数据类型处理完成。")

        logger.info("开始按IF排序...")
        # 按IF降序排序，将NaN值排在最后
        df_sorted = self.df_with_if.sort_values(by=self.if_col, ascending=False, na_position='last', ignore_index=True)
        logger.info("排序完成。")

        # 检查排序后的DataFrame
        if df_sorted.empty:
            error_msg = "输入的DataFrame为空。"
            logger.error(error_msg)
            # 返回空的DataFrame，列结构与原数据一致
            return df_sorted

            # 返回前 top_n 篇论文
        top_papers = df_sorted.head(top_n)
        logger.info(f"成功获取IF最高的前 {len(top_papers)} 篇论文。")
        logger.debug(f"前 {top_n} 论文信息预览: \n{top_papers.head().to_string()}")
        return top_papers

    # 保留旧方法以保持向后兼容性（如果需要）
    def get_highest_if_paper(self):
        """
        兼容旧接口：根据获取到的影响因子，找出IF最高的一篇论文。
        """
        logger.info("调用旧接口 get_highest_if_paper")
        top_papers = self.get_top_papers(top_n=1)
        if not top_papers.empty:
            highest_if_row = top_papers.iloc[0]
            logger.info(f"找到IF最高的论文，IF值为: {highest_if_row[self.if_col]}")
            return highest_if_row
        else:
            logger.warning("未能找到IF最高的论文。")
            return None

    def get_sorted_papers(self, ascending=False):
        """
        获取按影响因子排序后的完整DataFrame副本。
        """
        logger.info(f"开始获取完整排序列表 (升序: {ascending})...")
        # 确保IF已获取
        if self.if_col not in self.df_with_if.columns or self.df_with_if[self.if_col].isna().all():
            logger.info("排序前需要获取IF...")
            self.fetch_all_if()

        # 确保IF列是数值类型
        self.df_with_if[self.if_col] = pd.to_numeric(self.df_with_if[self.if_col], errors='coerce')

        # 排序
        df_sorted = self.df_with_if.sort_values(by=self.if_col, ascending=ascending, na_position='last',
                                                ignore_index=True)
        logger.info("完整排序列表获取完成。")
        return df_sorted.copy()  # 返回副本以避免修改内部数据


# --- 使用示例 ---
if __name__ == '__main__':
    # 配置主模块的日志
    main_logger = logging.getLogger('main')
    if not main_logger.handlers:
        main_fh = logging.FileHandler('main.log', encoding='utf-8')
        main_ch = logging.StreamHandler()
        main_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        main_fh.setFormatter(main_formatter)
        main_ch.setFormatter(main_formatter)
        main_logger.addHandler(main_fh)
        main_logger.addHandler(main_ch)
        main_logger.setLevel(logging.INFO)

    main_logger.info("=== 程序启动 ===")

    sample_data = {
        '标题': ['Shaping the future of precision medicine: plasma proteomics to uncover insights in thrombosis.'],
        '网站': ['https://pubmed.ncbi.nlm.nih.gov/40472045/  '],
        '摘要': [
            'Advances in various proteomics technologies, especially high-throughput and reproducibility, have enabled the systematic exploration of the circulating thrombosis proteome...'],
        '期刊': ['Expert review of proteomics'],
        '年限': [2025],
        '作者': ['Emil Johansson, Maria Jesus Iglesias, Jacob Odeberg, Fredrik Edfors']
    }
    df = pd.DataFrame(sample_data)

    # 如果您的DataFrame列名是英文的，请相应调整
    df.rename(columns={
        '标题': 'Title',
        '网站': 'URL',
        '摘要': 'Abstract',
        '期刊': 'Journal',
        '年限': 'Year',
        '作者': 'Authors'
    }, inplace=True)

    main_logger.info("原始数据:")
    main_logger.info(f"\n{df.to_string()}")
    main_logger.info("-" * 50)

    # 注意：这里 journal_column_name 应该是 'Journal' (大写J)，与rename后的一致
    API_KEY = 'key'
    main_logger.info("创建 PaperRankerByIF 实例...")
    ranker = PaperRankerByIF(df, journal_column_name='Journal', api_key=API_KEY)  # 修正列名

    main_logger.info("调用 get_top_papers(10)...")
    top_10_papers = ranker.get_top_papers(10)  # 获取前10

    if not top_10_papers.empty:
        main_logger.info("\nIF最高的前10篇论文是:")
        main_logger.info(f"\n{top_10_papers.to_string(index=False)}")  # index=False 不显示行索引
    else:
        main_logger.warning("\n未能找到任何论文。")

    main_logger.info("=== 程序结束 ===")
