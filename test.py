from playwright.sync_api import sync_playwright

def main():
    url = "https://scholar.google.com/scholar?as_q=&as_epq=VTE&as_oq=&as_eq=&as_occt=title"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # 第一步：直接进入 Scholar 搜索页
        print("👉 打开 Google Scholar 检索结果页")
        page.goto(url)

        input("✅ 已加载 Scholar 结果页，按回车退出...")
        browser.close()

if __name__ == "__main__":
    main()
