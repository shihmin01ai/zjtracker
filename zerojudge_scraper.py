import requests
from bs4 import BeautifulSoup
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class ZeroJudgeScraper:
    def __init__(self, course_url, account=None, password=None):
        self.course_url = course_url
        self.account = account
        self.password = password
        self.session = requests.Session()
        # 模擬常見的瀏覽器 User-Agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def login(self):
        """
        自動登入 ZeroJudge
        """
        if not self.account or not self.password:
            logger.error("未提供帳號或密碼，無法自動登入。")
            return False

        logger.info(f"嘗試為帳號 '{self.account}' 執行自動登入...")
        try:
            logger.info("步驟 1/3：取得登入頁面與安全憑證...")
            # 1. 先造訪登入頁面獲取 CSRF Token & 初始化 Cookie
            login_page_url = "https://zerojudge.tw/Login"
            resp = self.session.get(login_page_url)
            
            logger.info("步驟 2/3：解析網頁取得 CSRF Token...")
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 從 meta 標籤提取 csrfToken
            csrf_meta = soup.find('meta', {'name': 'csrfToken'})
            csrf_token = csrf_meta['content'] if csrf_meta else ""
            
            if not csrf_token:
                logger.warning("在頁面中沒找到 csrfToken，可能會登入失敗。")

            logger.info("步驟 3/3：打包帳號與憑證進行驗證...")
            # 2. 執行 POST 登入
            payload = {
                'account': self.account,
                'passwd': self.password
            }
            headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRF-Token': csrf_token,
                'Referer': login_page_url
            }
            
            login_resp = self.session.post(login_page_url, data=payload, headers=headers)
            
            if login_resp.status_code == 200:
                logger.info("自動登入成功！")
                new_sid = self.session.cookies.get('JSESSIONID')
                return new_sid
            else:
                logger.error(f"登入失敗 (狀態碼: {login_resp.status_code}): {login_resp.text[:100]}")
                return None
                
        except Exception as e:
            logger.error(f"自動登入過程中發生錯誤: {e}")
            return None

    def get_assignment_list(self, vclass_url):
        """
        自動偵測課程主頁 (ShowVClass) 中的所有作業/競賽連結
        """
        logger.info(f"正在偵測課程作業清單: {vclass_url}")
        resp = self.session.get(vclass_url)
        
        # 檢查是否被導向登入頁面或偵測到需要登入
        if "Login" in resp.url or "偵測到『登入』字眼" in resp.text or resp.status_code == 403:
            logger.warning("Session 已過期或未登入，嘗試自動登入...")
            if self.login():
                resp = self.session.get(vclass_url)
            else:
                logger.error("自動登入失敗，請檢查帳號密碼或手動更新 JSESSIONID。")
                return []
        
        if '登入' in resp.text and len(resp.text) < 50000:
             logger.warning("頁面內容過少且包含『登入』字眼，嘗試自動登入...")
             if self.login():
                 resp = self.session.get(vclass_url)
             else:
                 return []

        if resp.status_code != 200:
            logger.error("無法存取課程頁面")
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        assignments = []
        
        for a_ranking in soup.find_all('a', href=True):
            href = a_ranking['href']
            if 'ContestRanking' in href:
                title = ""
                panel = a_ranking.find_parent(class_='panel')
                if panel:
                    title_elem = panel.find(class_='panel-title')
                    if title_elem:
                        main_link = title_elem.find('a', attrs={'data-toggle': 'collapse'})
                        target_elem = main_link if main_link else title_elem
                        pull_right = target_elem.find(class_='pull-right')
                        if pull_right:
                            clean_soup = BeautifulSoup(str(pull_right), 'html.parser')
                            for tag in clean_soup.find_all(['span', 'i', 'button', 'div']):
                                if tag.get('class') and any(c in tag.get('class') for c in ['badge', 'modal', 'btn']):
                                    tag.decompose()
                            title = clean_soup.get_text().strip()
                        
                        if not title:
                            clean_soup = BeautifulSoup(str(target_elem), 'html.parser')
                            for tag in clean_soup.find_all(['span', 'i', 'button', 'div']):
                                if tag.get('class') and any(c in tag.get('class') for c in ['badge', 'modal', 'btn']):
                                    tag.decompose()
                            raw_text = clean_soup.get_text().strip()
                            title = re.sub(r'^\d+\.\s*', '', raw_text).strip()

                if not title or title == '測驗結果':
                    title = a_ranking.text.strip()
                
                if title:
                    title = re.sub(r'^\d+\.\s*', '', title)
                    title = title.strip()
                
                if not title or title == '測驗結果':
                    continue
                    
                full_url = f"https://zerojudge.tw/{href.lstrip('/')}" if not href.startswith('http') else href
                assignments.append({'title': title, 'url': full_url})
                logger.debug(f"成功識標: '{title}'")
                
        logger.info(f"偵測到 {len(assignments)} 個作業")
        return assignments

    def get_student_progress(self, target_url):
        """
        抓取特定作業/競賽的學生進度 (ContestRanking)
        """
        logger.info(f"正在抓取作業進度: {target_url}")
        resp = self.session.get(target_url)
        
        if "Login" in resp.url or "偵測到『登入』字眼" in resp.text:
            logger.warning("Session 已過期，嘗試自動登入...")
            if self.login():
                resp = self.session.get(target_url)
            else:
                return []
                
        soup = BeautifulSoup(resp.text, 'html.parser')
        students_data = []
        table = soup.find('table', {'id': 'datatable'}) or soup.find('table')
        if not table:
            logger.error("找不到資料表格")
            return []
        
        rows = table.find_all('tr')
        if not rows:
            return []
            
        header = []
        header_row_idx = -1
        keywords = ['User', '帳號', 'Rank', '名次', '使用者']
        
        for i, row in enumerate(rows):
            tds = row.find_all(['th', 'td'])
            texts = [td.text.strip() for td in tds]
            if any(k in texts for k in keywords):
                header = texts
                header_row_idx = i
                break
        
        if not header and rows:
            tds = rows[0].find_all(['th', 'td'])
            header = [td.text.strip() for td in tds]
            header_row_idx = 0

        if not header:
            logger.error("無法辨識表頭結構")
            return []

        for row in rows[header_row_idx + 1:]:
            cols = row.find_all(['td'])
            if len(cols) < 2: 
                continue
            
            student_info = {}
            for i in range(min(len(header), len(cols))):
                cell = cols[i]
                h_name = header[i].replace('\n', ' ').replace('\t', ' ').strip()
                h_name = ' '.join(h_name.split())
                cell_text = cell.text.strip()
                
                skip_status = any(x in h_name for x in ['身分', 'User', '帳號', '使用者', 'S/N', 'Rank', '名次', '分數', 'AC數', '時間', '排名', '註解'])
                
                if not skip_status:
                    if 'ac' in str(cell.get('class', [])) or 'Yes' in cell_text or '✅' in cell_text:
                        student_info[h_name] = '✅'
                    elif '(' in cell_text or (cell_text.isdigit() and int(cell_text) > 0):
                        student_info[h_name] = '⏳'
                    elif not cell_text or cell_text == '-' or cell_text == '0':
                        student_info[h_name] = '➖'
                    else:
                        student_info[h_name] = cell_text
                else:
                    student_info[h_name] = cell_text

            raw_id = student_info.get('身分') or ''
            if not raw_id or raw_id in ['✅', '⏳', '➖']:
                for k, v in student_info.items():
                    if k not in ['S/N', 'Rank', '名次', '分數', 'AC數', '時間', '排名'] and v not in ['✅', '⏳', '➖'] and not str(v).isdigit():
                        raw_id = v
                        break
            
            parentheses_match = re.search(r'\((.*?)\)', str(raw_id))
            if parentheses_match:
                clean_id = parentheses_match.group(1).strip()
            else:
                clean_id = str(raw_id).strip()
                if ' ' in clean_id:
                    parts = clean_id.split()
                    if parts[0].isdigit():
                        clean_id = ' '.join(parts[1:])
            
            student_info['_student_id'] = clean_id
            students_data.append(student_info)
            
        logger.info(f"成功抓取 {len(students_data)} 筆學生進度")
        return students_data

if __name__ == "__main__":
    pass
