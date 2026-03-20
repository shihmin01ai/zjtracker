import yaml
import logging
import os
import getpass
from zerojudge_scraper import ZeroJudgeScraper
from google_sheets_sync import GoogleSheetsSync

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def main():
    config_path = 'config.yaml'
    if not os.path.exists(config_path):
        logger.error(f"找不到設定檔: {config_path}")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    zj_conf = config['zerojudge']
    gs_conf = config['google_sheets']
    
    vclass_url = zj_conf['course_url']
    
    # 優先從環境變數讀取帳密
    account = os.environ.get('ZJ_ACCOUNT')
    password = os.environ.get('ZJ_PASSWORD')

    # 如果沒有帳密，則進行互動式詢問
    if not account:
        print("\n請輸入 ZeroJudge 帳號以進行登入 (此帳號不會被儲存):")
        account = input("帳號: ").strip()
    if not password:
        password = getpass.getpass("密碼: ")

    # 初始化爬蟲
    scraper = ZeroJudgeScraper(
        vclass_url, 
        account=account,
        password=password
    )
    
    # 強制先執行登入
    if not scraper.login():
        logger.error("無法登入 ZeroJudge，請檢查您的帳號密碼。")
        return

    assignments = scraper.get_assignment_list(vclass_url)
    
    if not assignments:
        logger.error("找不到任何作業連結，請確認課程主頁網址或登入狀態。")
        return

    # 準備 Google Sheets 同步
    if not os.path.exists(gs_conf['service_account_file']):
        logger.error(f"找不到 {gs_conf['service_account_file']}")
        return

    syncer = GoogleSheetsSync(
        gs_conf['spreadsheet_name'], 
        gs_conf['worksheet_name'], 
        gs_conf['service_account_file']
    )

    all_results = {}
    # 逐一抓取每個作業資料
    for assign in assignments:
        title = assign['title']
                  
        logger.info(f"正在抓取進度: {title}")
        
        student_data = scraper.get_student_progress(assign['url'])
        if student_data:
            all_results[title] = student_data
        else:
            logger.warning(f"作業 '{title}' 抓取失敗，跳過。")

    # 一次性同步所有結果至 Google Sheets
    if all_results:
        syncer.sync_all_assignments(all_results)
    
    logger.info("所有作業同步完成！")

if __name__ == "__main__":
    main()
