# app.py

import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
import os
import logging
from datetime import datetime
import json
import sys
import time
import shutil
import re

# 假设这些模块存在于你的项目中
from paper_api import PubMedSearcher
from compare_IF import PaperRankerByIF
from get_data_xhs import QuestionAnswerer
from translate import baidu_translate_if_chinese
from create_photo import Create_photo
from get_photo import get_screenshot_local

def extract_pmid_from_paper_url(url):
    """从论文URL中提取PMID"""
    if not url:
        return None
    try:
        pattern = r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)'
        match = re.search(pattern, url, re.IGNORECASE)
        return match.group(1) if match else None
    except Exception as e:
        app.logger.error(f"提取PMID失败 URL={url}: {e}")
        return None


def setup_logging():
    """设置应用日志"""
    if not os.path.exists('log'):
        os.makedirs('log')

    logger = logging.getLogger('paper_search_app')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    file_handler = logging.FileHandler('log/paper_search_app.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# 初始化Flask应用和日志
app_logger = setup_logging()
app = Flask(__name__, static_folder='static', static_url_path='/static')


def ensure_directories():
    """确保必要的目录存在"""
    directories = ['static', 'static/image', 'static/charts', 'log', 'dynamic_images']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            app_logger.info(f"创建目录: {directory}")


ensure_directories()


def safe_get_value(obj, key, default=''):
    """安全地从对象（dict或有属性的对象）中获取值"""
    try:
        if obj is None:
            return default
        if isinstance(obj, dict):
            value = obj.get(key, default)
        elif hasattr(obj, key):
            value = getattr(obj, key, default)
        else:
            value = default

        if pd.isna(value) or value is None:
            return default
        return str(value).strip()
    except Exception as e:
        app_logger.error(f"获取值时出错 key={key}: {e}")
        return default


@app.route('/api/search', methods=['POST'])
def api_search():
    """处理论文搜索请求"""
    start_time = time.time()
    try:
        data = request.get_json()
        if not data:
            app_logger.warning("收到无效的JSON数据")
            elapsed_time = (time.time() - start_time) * 1000
            app_logger.info(f"API搜索请求处理完成(无效数据) - 响应时间: {elapsed_time:.2f}ms")
            return jsonify({'result': '无效的请求数据'}), 400

        key1 = data.get('key1', '')
        key2 = data.get('key2', '')
        theme = data.get('theme', '')
        start_year = data.get('start_year', '')
        end_year = data.get('end_year', '')

        search_info = {
            'ip': request.remote_addr,
            'user_agent': str(request.user_agent),
            'timestamp': datetime.now().isoformat(),
            'search_params': {
                'key1': key1,
                'key2': key2,
                'theme': theme,
                'start_year': start_year,
                'end_year': end_year
            }
        }

        app_logger.info(f"收到检索请求: {json.dumps(search_info, ensure_ascii=False)}")
        # 截图KEY
        PAPER_KEY = 'PAPER_KEY'
        # 阿里云KEY
        API_KEY = 'API_KEY'

        # 构建查询
        query_parts = []
        if theme and theme.strip():
            theme = baidu_translate_if_chinese(theme, target_lang="en")
            query_parts.append(f'("{theme.strip()}"[Title]')
        if key1 and key1.strip():
            key1 = baidu_translate_if_chinese(key1, target_lang="en")
            query_parts.append(f'AND "{key1.strip()}"[Title/Abstract])')
        if key2 and key2.strip():
            key2 = baidu_translate_if_chinese(key2, target_lang="en")
            query_parts.append(f'AND "{key2.strip()}"[Journal]')
        query = " ".join(query_parts)
        app_logger.info(f'检索内容为:{query}')

        # PubMed搜索
        app_logger.info("开始PubMed搜索...")
        searcher = PubMedSearcher(query, PAPER_KEY, year_start=int(start_year), year_end=int(end_year))
        papers = searcher.run()
        app_logger.info(f"PubMed搜索完成，找到 {len(papers)} 篇论文")

        if len(papers) == 0:
            app_logger.info(f'抱歉未找到相关文献，请重新选择检索标准')
            elapsed_time = (time.time() - start_time) * 1000
            app_logger.info(f"API搜索请求处理完成 - 响应时间: {elapsed_time:.2f}ms")
            return jsonify({
                'result': '(｡•́︿•̀｡) 抱歉\n未找到相关文献，请重新选择检索标准'
            })

        # 论文排名 (按影响因子排序)
        app_logger.info("开始论文排名...")
        ranker = PaperRankerByIF(pd.DataFrame(papers), journal_column_name='journal', api_key=API_KEY)

        # 获取按IF排序的前10篇论文
        top_papers_df = ranker.get_top_papers(top_n=10)
        app_logger.info(f"论文排名完成，获取到 {len(top_papers_df)} 篇论文 (最多10篇)")

        # 准备表格数据
        table_data = []
        for i, (_, paper) in enumerate(top_papers_df.iterrows()):
            title = safe_get_value(paper, 'title', '无标题')
            journal = safe_get_value(paper, 'journal', '无期刊信息')
            pub_date = safe_get_value(paper, 'year', '无日期')
            url = safe_get_value(paper, 'url', '#')
            abstract = safe_get_value(paper, 'abstract', '')

            # 获取影响因子并格式化
            impact_factor = paper.get('影响因子', 'N/A')
            if pd.isna(impact_factor) or impact_factor is None or impact_factor == 'N/A':
                impact_factor_str = 'N/A'
            else:
                try:
                    impact_factor_str = f"{float(impact_factor):.2f}"
                except (ValueError, TypeError):
                    impact_factor_str = 'N/A'

            table_data.append({
                'id': i,
                'title': title[:100] + '...' if len(title) > 100 else title,
                'journal': journal,
                'pub_date': pub_date,
                'url': url,
                'abstract': abstract,
                'impact_factor': impact_factor_str
            })

        elapsed_time = (time.time() - start_time) * 1000
        app_logger.info(f"API搜索请求处理完成 - 响应时间: {elapsed_time:.2f}ms")

        return jsonify({
            'papers': table_data,
            'status': 'success'
        })

    except Exception as e:
        error_msg = f"检索处理出错: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        elapsed_time = (time.time() - start_time) * 1000
        app_logger.info(f"API搜索请求处理完成(错误) - 响应时间: {elapsed_time:.2f}ms")
        return jsonify({'result': f'检索出错：{str(e)}'}), 500


@app.route('/api/get_paper_summary', methods=['POST'])
def get_paper_summary():
    """获取单篇论文的总结"""
    start_time = time.time()
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        paper_id = data.get('paper_id')
        paper_data = data.get('paper_data')

        if paper_id is None or not paper_data:
            return jsonify({'error': '缺少论文ID或数据'}), 400

        API_KEY = 'your_key'

        # 使用前端传来的论文数据
        title = safe_get_value(paper_data, 'title')
        url = safe_get_value(paper_data, 'url')
        abstract = safe_get_value(paper_data, 'abstract')

        paper_data_str = f"title:{title}\nurl:{url}\nabstract:{abstract}"

        summary = "无法生成总结"
        if paper_data_str:
            try:
                app_logger.info(f"开始生成论文{paper_id}的总结...")
                qa_agent_v3 = QuestionAnswerer(api_key=API_KEY, model_name="deepseek-v3")
                summary = qa_agent_v3.ask(paper_data_str)
                app_logger.info(f"论文{paper_id}总结生成完成")
            except Exception as e:
                app_logger.error(f"生成论文{paper_id}总结失败: {e}", exc_info=True)
                summary = "总结生成失败"

        elapsed_time = (time.time() - start_time) * 1000
        app_logger.info(f"论文总结请求处理完成 - 响应时间: {elapsed_time:.2f}ms")

        return jsonify({
            'summary': summary,
            'status': 'completed'
        })

    except Exception as e:
        app_logger.error(f"论文总结处理出错: {str(e)}", exc_info=True)
        elapsed_time = (time.time() - start_time) * 1000
        app_logger.info(f"论文总结请求处理完成(错误) - 响应时间: {elapsed_time:.2f}ms")
        return jsonify({'error': f'处理出错：{str(e)}'}), 500


@app.route('/api/generate_images', methods=['POST'])
def generate_images():
    """为指定论文生成图片"""
    start_time = time.time()
    try:
        data = request.get_json()
        paper_id = data.get('paper_id')
        paper_data = data.get('paper_data')

        if paper_id is None or not paper_data:
            return jsonify({'error': '缺少论文ID或数据'}), 400

        API_KEY = 'your_key'

        app_logger.info(f"开始为论文{paper_id}生成图片...")

        # 获取论文数据
        title = safe_get_value(paper_data, 'title')
        url = safe_get_value(paper_data, 'url')
        abstract = safe_get_value(paper_data, 'abstract')

        # 提取PMID用于文件命名
        path = extract_pmid_from_paper_url(url) if url else f"paper_{paper_id}_{int(time.time())}"

        image2_url = None
        ai_image_url = None

        # 截图处理
        if url:
            screenshot_filename = f'screenshot_{path}.jpg'
            screenshot_filepath = os.path.join('dynamic_images', screenshot_filename)

            # 检查截图文件是否已存在
            if os.path.exists(screenshot_filepath) and os.path.getsize(screenshot_filepath) > 0:
                image2_url = f"dynamic_images/{screenshot_filename}"
                app_logger.info(f"使用已存在的截图: {screenshot_filepath}")
            else:
                try:
                    app_logger.info(f"开始进行截图到: {screenshot_filepath}")
                    get_screenshot_local(url, "01989db5-12f7-772d-8a32-6e3bb031c3b3", screenshot_filepath)

                    if os.path.exists(screenshot_filepath) and os.path.getsize(screenshot_filepath) > 0:
                        image2_url = f"dynamic_images/{screenshot_filename}"
                        app_logger.info(f"截图完成: {screenshot_filepath}")
                    else:
                        app_logger.warning(f"截图文件未生成或为空: {screenshot_filepath}")
                except Exception as e:
                    app_logger.error(f"截图失败: {e}", exc_info=True)

        # AI图片生成
        paper_data_str = f"title:{title}\nabstract:{abstract}" if title else "无论文数据"

        if paper_data_str and paper_data_str != "无论文数据":
            ai_filename = f'Ai_{path}.jpg'
            ai_filepath = os.path.join('dynamic_images', ai_filename)

            # 检查AI图片文件是否已存在
            if os.path.exists(ai_filepath) and os.path.getsize(ai_filepath) > 0:
                ai_image_url = f"dynamic_images/{ai_filename}"
                app_logger.info(f"使用已存在的AI图片: {ai_filepath}")
            else:
                try:
                    app_logger.info(f"开始生成AI图片到: {ai_filepath}")
                    photo_creator = Create_photo(api_key=API_KEY, file_name=ai_filepath)
                    file_path = photo_creator.create(paper_data_str)

                    if file_path and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        if not os.path.exists(ai_filepath):
                            shutil.copy2(file_path, ai_filepath)
                        ai_image_url = f"dynamic_images/{ai_filename}"
                        app_logger.info(f"AI图片生成完成: {ai_filepath}")
                    else:
                        app_logger.warning(f"AI图片未生成或为空: {file_path}")
                except Exception as e:
                    app_logger.error(f"创建AI图片失败: {e}", exc_info=True)

        # 返回图片URL
        images_result = [
            f'主页截图链接:{str(image2_url or "暂无")}',
            f'AI插图链接:{str(ai_image_url or "暂无")}'
        ]
        images_result = '\n\n'.join(images_result)

        app_logger.info(f'图片地址: {images_result}')

        elapsed_time = (time.time() - start_time) * 1000
        app_logger.info(f"图片生成请求处理完成 - 响应时间: {elapsed_time:.2f}ms")

        return jsonify({
            'result': images_result,
            'status': 'completed'
        })

    except Exception as e:
        app_logger.error(f"图片生成处理出错: {str(e)}", exc_info=True)
        elapsed_time = (time.time() - start_time) * 1000
        app_logger.info(f"图片生成请求处理完成(错误) - 响应时间: {elapsed_time:.2f}ms")
        return jsonify({'error': f'图片生成出错：{str(e)}'}), 500


# 提供动态生成的图片文件
@app.route('/dynamic_images/<path:filename>')
def serve_dynamic_image(filename):
    """提供动态生成的图片文件"""
    try:
        if '..' in filename or filename.startswith('/'):
            app_logger.warning(f"尝试访问非法文件路径: {filename}")
            return "无效的文件名", 400

        file_path = os.path.join('dynamic_images', filename)
        app_logger.info(f"请求动态图片: {file_path}")

        if os.path.exists(file_path):
            return send_from_directory('dynamic_images', filename)
        else:
            app_logger.warning(f"动态图片未找到: {file_path}")
            return "图片未找到", 404

    except Exception as e:
        app_logger.error(f"提供动态图片失败 {filename}: {e}")
        return "服务器错误", 500


# 提供主页
@app.route('/')
def index():
    """提供主页HTML文件"""
    start_time = time.time()
    app_logger.info(f"用户访问首页 - IP: {request.remote_addr}, User-Agent: {request.user_agent}")
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            app_logger.info("成功加载首页HTML文件")
            response_content = f.read()
            elapsed_time = (time.time() - start_time) * 1000
            app_logger.info(f"首页请求处理完成 - 响应时间: {elapsed_time:.2f}ms")
            return response_content
    except FileNotFoundError:
        error_msg = "错误：找不到 index.html 文件"
        app_logger.error(error_msg)
        elapsed_time = (time.time() - start_time) * 1000
        app_logger.info(f"首页请求处理完成(错误) - 响应时间: {elapsed_time:.2f}ms")
        return '<h1>错误：找不到 index.html 文件</h1><p>请确保 index.html 文件与 app.py 在同一目录下</p>'


# 提供静态文件
@app.route('/static/<path:filename>')
def custom_static(filename):
    """提供静态文件"""
    start_time = time.time()
    try:
        app_logger.debug(f"提供静态文件: {filename}")
        response = send_from_directory(app.static_folder, filename)
        response.headers['Cache-Control'] = 'public, max-age=3600'
        elapsed_time = (time.time() - start_time) * 1000
        app_logger.info(f"静态文件请求处理完成 - 文件: {filename}, 响应时间: {elapsed_time:.2f}ms")
        return response
    except Exception as e:
        app_logger.error(f"提供静态文件失败 {filename}: {e}")
        elapsed_time = (time.time() - start_time) * 1000
        app_logger.info(f"静态文件请求处理完成(错误) - 文件: {filename}, 响应时间: {elapsed_time:.2f}ms")
        return jsonify({'error': 'File not found'}), 404


# 请求前钩子
@app.before_request
def log_request_info():
    """记录请求信息"""
    request.start_time = time.time()
    if request.endpoint and request.endpoint not in ['static', 'custom_static', 'serve_dynamic_image']:
        app_logger.info(f"收到请求 - 方法: {request.method}, 路径: {request.path}, IP: {request.remote_addr}")


# 响应后钩子
@app.after_request
def log_response_info(response):
    """记录响应信息"""
    if request.endpoint and request.endpoint not in ['static', 'custom_static', 'serve_dynamic_image']:
        if hasattr(request, 'start_time'):
            elapsed_time = (time.time() - request.start_time) * 1000
            app_logger.info(
                f"响应完成 - 状态码: {response.status_code}, 路径: {request.path}, 内容长度: {response.content_length or 0}, 响应时间: {elapsed_time:.2f}ms")
        else:
            app_logger.info(
                f"响应完成 - 状态码: {response.status_code}, 路径: {request.path}, 内容长度: {response.content_length or 0}")
    return response


# 应用入口
if __name__ == '__main__':
    print("正在启动论文检索系统...")
    print("请在浏览器中访问: http://0.0.0.0:5000")

    if os.path.exists('index.html'):
        app_logger.info("✓ 找到 index.html 文件，系统启动成功")
        print("✓ 找到 index.html 文件")
    else:
        app_logger.warning("✗ 警告：未找到 index.html 文件")
        print("✗ 警告：未找到 index.html 文件")

    app.run(debug=False, host='0.0.0.0', port=5000)