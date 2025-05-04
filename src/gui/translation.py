from utils import get_logger

logger = get_logger()

class TranslationManager:
    """Handles language translations for the UI"""
    TRANSLATIONS = {
        "en": {
            "initializing_services": "Initializing services...",
            "cleaning": "start cleaning...",
            "cleaning_files": "Cleaning files: {}",
            "statement_items_found": "Statement contains {} items to match",
            "statement_length_warning": "Warning: Could not determine statement length, using default",
            "performing_matching": "Performing transaction matching...",
            "matching_details": "Matching transactions: {:.2f}% complete ({}/{})",
            "saving_reports": "Saving reports...",
            "window_title": "Transaction Matcher",
            "files_tab": "Files",
            "settings_tab": "Settings",
            "process_tab": "Process",
            "input_files": "Input Files",
            "language": "Language:",
            "thai": "Thai",
            "english": "English",
            "purchase_tax": "Purchase Tax Report (.csv):",
            "sales_tax": "Sales Tax Report (.csv):",
            "withholding_tax": "Withholding Tax Report (.xlsx):",
            "bank_statement": "Bank Statement (.xlsx):",
            "output_dir": "Output Directory:",
            "browse_file": "Browse File",
            "browse_dir": "Browse Directory",
            "open": "Open", 
            "reset": "Reset",
            "start_processing": "Start Processing",
            "exit": "Exit",
            "copy_clipboard": "Copy to Clipboard",
            "settings": "Settings",
            "sheet": "Sheet:",
            "font_size": "Font Size",
            "matching_params": "Matching Parameters",
            "matching_credit_days": "Credit Days:",
            "matching_sale_tolerance": "Sale Tolerance:",
            "matching_purchase_tolerance": "Purchase Tolerance:",
            "open_dir": "Open Directory",
            "open_output": "Open Output Directory",
            "status": "Status",
            "elapsed": "Elapsed:",
            "eta": "ETA:",
            "items": "Items:",
            "ready": "Ready",
            "complete": "Complete",
            "missing_files": "Please select the following files:",
            "error": "Error",
            "developer_error": "Developer Error Details",
            "success": "Success",
            "processing_complete": "Processing complete! Reports saved to: {}",
            "avg_time": "Avg Time: {}",
            "items_processed": "Processed: {}/{}"
        },
        "th": {
            "initializing_services": "กำลังเตรียมระบบให้พร้อมใช้งาน...",
            "cleaning": "เริ่มกระบวนการทำความสะอาด...",
            "cleaning_files": "กำลังทำความสะอาดไฟล์: {} ({}/{})",
            "statement_items_found": "พบรายการในสเตทเม้นท์ {} รายการที่ต้องจับคู่",
            "statement_length_warning": "คำเตือน: ไม่สามารถระบุจำนวนรายการได้ ใช้ค่าเริ่มต้นแทน",
            "performing_matching": "กำลังดำเนินการจับคู่ธุรกรรม...",
            "matching_details": "กำลังจับคู่ธุรกรรม: {:.2f}% เสร็จสิ้น ({}/{})",
            "saving_reports": "กำลังบันทึกรายงาน...",
            "window_title": "โปรแกรมจับคู่ธุรกรรม",
            "files_tab": "ไฟล์",
            "settings_tab": "ตั้งค่า",
            "process_tab": "ประมวลผล",
            "input_files": "ไฟล์นำเข้า",
            "language": "ภาษา:",
            "thai": "ไทย",
            "english": "English",
            "purchase_tax": "รายงานภาษีซื้อ (.csv):",
            "sales_tax": "รายงานภาษีขาย (.csv):",
            "withholding_tax": "รายงานภาษีหัก ณ ที่จ่าย (.xlsx):",
            "bank_statement": "รายการเดินบัญชี (.xlsx):",
            "output_dir": "โฟลเดอร์ผลลัพธ์:",
            "browse_file": "เลือกไฟล์",
            "browse_dir": "เลือกโฟลเดอร์",
            "open": "เปิด",
            "reset": "รีเซ็ต",
            "start_processing": "เริ่มการประมวลผล",
            "exit": "ออก",
            "copy_clipboard": "คัดลอกไปคลิปบอร์ด",
            "settings": "การตั้งค่า",
            "sheet": "ชีต:",
            "font_size": "ขนาดตัวอักษร",
            "matching_params": "เงื่อนไขการจับคู่",
            "matching_credit_days": "ระยะเวลาเครดิต:",
            "matching_sale_tolerance": "ความคลาดเคลื่อนการขาย:",
            "matching_purchase_tolerance": "ความคลาดเคลื่อนการซื้อ:",
            "open_dir": "เปิดโฟลเดอร์",
            "open_output": "เปิดโฟลเดอร์ผลลัพธ์",
            "status": "สถานะ",
            "elapsed": "เวลาที่ใช้:",
            "eta": "เวลาที่คาดว่าเหลือ:",
            "items": "จำนวน:",
            "ready": "พร้อมใช้งาน",
            "complete": "เสร็จสิ้น",
            "missing_files": "กรุณาเลือกไฟล์ต่อไปนี้:",
            "error": "ข้อผิดพลาด",
            "developer_error": "รายละเอียดข้อผิดพลาดสำหรับนักพัฒนา",
            "success": "สำเร็จ",
            "processing_complete": "ประมวลผลเสร็จสิ้น! บันทึกผลลัพธ์ที่: {}",
            "avg_time": "เวลาเฉลี่ย: {}",
            "items_processed": "ประมวลผลแล้ว: {}/{}"
        }
    }

    @classmethod
    def get_translation(cls, language: str, key: str, *format_args) -> str:
        """Get translation for a key in the specified language"""
        try:
            translation = cls.TRANSLATIONS[language][key]
            if format_args:
                return translation.format(*format_args)
            return translation
        except KeyError:
            logger.warning(f"Missing translation for key: {key}")
            return key