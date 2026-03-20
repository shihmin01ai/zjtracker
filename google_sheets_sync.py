import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging

logger = logging.getLogger(__name__)

class GoogleSheetsSync:
    def __init__(self, spreadsheet_name, worksheet_name, service_account_file):
        self.scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        self.creds = ServiceAccountCredentials.from_json_keyfile_name(service_account_file, self.scope)
        self.client = gspread.authorize(self.creds)
        try:
            self.spreadsheet = self.client.open(spreadsheet_name)
        except gspread.exceptions.SpreadsheetNotFound:
            # 偵錯用：列出所有可存取的試算表
            all_spreadsheets = self.client.openall()
            available_names = [s.title for s in all_spreadsheets]
            logger.error(f"找不到試算表: '{spreadsheet_name}'")
            logger.error(f"目前 Service Account 可存取的試算表列表: {available_names}")
            raise
        self.worksheet = self.spreadsheet.worksheet(worksheet_name)
        self.headers = None

    def ensure_column(self, assignment_name):
        """
        檢查標題列是否已有該作業，若無則新增至最後一欄
        """
        if self.headers is None:
            all_values = self.worksheet.get_all_values()
            if not all_values:
                self.worksheet.update_cell(1, 1, "姓名/帳號")
                self.headers = ["姓名/帳號"]
            else:
                self.headers = all_values[0]
            
        # 檢查是否存在 (不分空格)
        existing_headers = [h.strip() for h in self.headers]
        if assignment_name.strip() not in existing_headers:
            new_col_idx = len(self.headers) + 1
            
            # 檢查試算表欄位數是否足夠，若不足則擴張
            if new_col_idx > self.worksheet.col_count:
                logger.debug(f"擴張試算表欄位數: {self.worksheet.col_count} -> {new_col_idx}")
                self.worksheet.add_cols(10) # 一次多補 10 欄減少 API 呼叫
            
            logger.info(f"自動新增標題欄位: '{assignment_name}' 於第 {new_col_idx} 欄")
            self.worksheet.update_cell(1, new_col_idx, assignment_name.strip())
            # 更新快取
            self.headers.append(assignment_name.strip())
            return new_col_idx
        
        return existing_headers.index(assignment_name.strip()) + 1

    def sync_all_assignments(self, all_results):
        """
        一次同步多個作業的資料，減少 API 呼叫次數
        all_results: { '作業名稱': [學生資料列表], ... }
        """
        if not all_results:
            return

        logger.info(f"開始批次同步 {len(all_results)} 個作業...")
        
        # 1. 確保所有標題欄位都存在
        for title in all_results.keys():
            self.ensure_column(title)
            
        # 2. 抓取最新資料狀態 (一次讀取)
        all_values = self.worksheet.get_all_values()
        if not all_values:
            logger.warning("工作表是空的。")
            return
            
        self.headers = all_values[0]
        headers = self.headers
        
        # 建立學生 ID 到列索引的映射，加速查詢
        student_id_to_row = {str(row[0]).strip(): i + 1 for i, row in enumerate(all_values)}
        
        # 建立標題到欄索引的映射
        header_to_col = {h.strip(): i + 1 for i, h in enumerate(headers)}
        
        cells_to_update = []
        
        # 3. 遍歷所有作業數據
        for title, students_data in all_results.items():
            col_idx = header_to_col.get(title.strip())
            if not col_idx:
                continue
                
            for student in students_data:
                student_id = student.get('_student_id')
                if not student_id:
                    continue
                    
                row_idx = student_id_to_row.get(str(student_id).strip())
                if not row_idx:
                    continue
                    
                score = student.get('分數') or student.get('Score') or '0'
                time = student.get('時間') or student.get('Time') or '0'
                combined_value = f"{score} / {time}"
                
                cells_to_update.append(gspread.cell.Cell(row=row_idx, col=col_idx, value=combined_value))

        # 4. 執行大批次更新
        if cells_to_update:
            logger.info(f"正在執行大批次更新，共 {len(cells_to_update)} 筆儲存格資料...")
            # 如果資料量極大，可以考慮切片更新，但一般課程規模 1000 筆內沒問題
            self.worksheet.update_cells(cells_to_update)
            logger.info("批次同步完成！")

    def update_assignment_data(self, assignment_name, students_data):
        # 保持舊方法相容性，但內部可以改用批次邏輯
        self.sync_all_assignments({assignment_name: students_data})

if __name__ == "__main__":
    pass
