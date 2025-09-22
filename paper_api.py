import requests
import xml.etree.ElementTree as ET
import openpyxl
import logging
import os

log_dir = 'log'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

def setup_logger():
    logger = logging.getLogger('pubmed_search')
    logger.setLevel(logging.INFO)

    logger.handlers.clear()

    file_handler = logging.FileHandler(
        filename='log/paper_search.log',
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


class PubMedSearcher:
    def __init__(self, query, api_key, retmax=20, year_start=None, year_end=None):
        self.query = query
        self.api_key = api_key
        self.retmax = retmax
        self.year_start = year_start
        self.year_end = year_end

    def search_pubmed(self):
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": self.query,
            "retmax": self.retmax,
            "retmode": "json",
            "api_key": self.api_key
        }
        try:
            logger.info(f"开始 PubMed 搜索: {self.query}")
            r = requests.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            pmid_list = data['esearchresult']['idlist']
            logger.info(f"PubMed 搜索成功，找到 {len(pmid_list)} 篇文章")
            return pmid_list
        except Exception as e:
            logger.error(f"PubMed 搜索出错: {e}")
            return []

    def fetch_details(self, pmids):
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "api_key": self.api_key
        }
        try:
            logger.info(f"开始获取 {len(pmids)} 篇文章的详细信息")
            r = requests.get(url, params=params)
            r.raise_for_status()
            logger.info(f"成功获取文章详情")
            return r.text
        except Exception as e:
            logger.error(f"获取文章详情时出错: {e}")
            return ""

    def get_year(self, article):
        year = article.findtext('.//PubDate/Year')
        if not year:
            medline_date = article.findtext('.//PubDate/MedlineDate')
            if medline_date:
                year = medline_date.split(' ')[0][:4]
        if not year:
            article_date = article.findtext('.//ArticleDate/Year')
            if article_date:
                year = article_date
        return year

    def parse_details(self, xml_data):
        try:
            root = ET.fromstring(xml_data)
        except Exception as e:
            logger.error(f"解析 XML 数据时出错: {e}")
            return []

        papers = []
        for article in root.findall('.//PubmedArticle'):
            year = self.get_year(article)

            if self.year_start is not None and self.year_end is not None:
                if not year or not year.isdigit():
                    logger.debug("文章年份无效，跳过")
                    continue
                if int(year) < self.year_start or int(year) > self.year_end:
                    logger.debug(f"文章年份 {year} 不在 {self.year_start}-{self.year_end} 范围内，跳过")
                    continue

            title = article.findtext('.//ArticleTitle', default='').strip()
            pmid = article.findtext('.//PMID', default='').strip()
            url = f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/' if pmid else ''

            abstract_texts = article.findall('.//AbstractText')
            abstract = ' '.join([abst.text.strip() for abst in abstract_texts if abst.text]) if abstract_texts else ''

            journal = article.findtext('.//Journal/Title', default='').strip()

            authors = []
            for author in article.findall('.//Author'):
                lastname = author.findtext('LastName', '').strip()
                firstname = author.findtext('ForeName', '').strip()
                if lastname and firstname:
                    authors.append(f"{firstname} {lastname}")
                elif lastname:
                    authors.append(lastname)

            paper_info = {
                'title': title,
                'url': url,
                'abstract': abstract,
                'journal': journal,
                'year': year,
                'authors': ', '.join(authors)
            }

            papers.append(paper_info)

        logger.info(f"成功解析 {len(papers)} 篇文章")
        return papers

    def run(self):
        logger.info("开始执行 PubMed 搜索流程")
        pmids = self.search_pubmed()
        if not pmids:
            logger.warning("未找到任何 PMID，流程结束")
            return []

        xml_data = self.fetch_details(pmids)
        if not xml_data:
            logger.warning("未获取到 XML 数据，流程结束")
            return []

        papers = self.parse_details(xml_data)
        logger.info(f"PubMed 搜索流程完成，共获得 {len(papers)} 篇文章")
        return papers

    def save_to_excel(self, papers, filename="pubmed_results.xlsx"):
        try:
            logger.info(f"开始保存 {len(papers)} 篇文章到 Excel 文件: {filename}")
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "PubMed Results"

            ws.append(['标题', '网站', '摘要', '期刊', '年限', '作者'])

            for p in papers:
                ws.append([
                    p['Title'],
                    p['URL'],
                    p['Abstract'],
                    p['Journal'],
                    p['Year'],
                    p['Authors']
                ])

            wb.save(filename)
            logger.info(f"成功保存结果到 Excel 文件: {filename}")
        except Exception as e:
            logger.error(f"保存 Excel 文件时出错: {e}")


if __name__ == "__main__":
    query = 'VTE AND journal:"Expert review of proteomics"'
    PAPER_KEY = 'key'
    retmax = 20
    year_start = 2022
    year_end = 2026

    logger.info("=== PubMed 搜索程序启动 ===")
    logger.info(f"搜索查询: {query}")
    logger.info(f"年份范围: {year_start} - {year_end}")
    logger.info(f"最大返回结果数: {retmax}")

    searcher = PubMedSearcher(query, PAPER_KEY, retmax=retmax, year_start=year_start, year_end=year_end)
    papers = searcher.run()

    if papers:
        logger.info(f"找到 {len(papers)} 篇文章，开始输出详细信息:")
        for i, p in enumerate(papers, 1):
            logger.info(f"\n--- 文章 {i} ---")
            logger.info(f"标题: {p['title']}")
            logger.info(f"网站: {p['url']}")
            logger.info(f"期刊: {p['journal']}")
            logger.info(f"年限: {p['year']}")
            logger.info(f"作者: {p['authors']}")
            abstract_preview = p['abstract'][:200] + "..." if len(p['abstract']) > 200 else p['abstract']
            logger.info(f"摘要预览: {abstract_preview}")

        searcher.save_to_excel(papers, filename="pubmed_results.xlsx")
        logger.info("结果已保存到 pubmed_results.xlsx")
    else:
        logger.warning("未找到符合条件的文章")

    logger.info("=== PubMed 搜索程序结束 ===")