import os 

CONFIG = {
    'csv_exported_purchase_tax_report': r'data/inputs/ภาษีซื้อ-ทรัพยเจิรญ67.csv', # r for non-ascii text
    'csv_exported_sales_tax_report': r'data/inputs/ภาษีขาย-ทรัพย์เจริญ67.csv',
    'excel_Withholding_tax_report': r'data/inputs/ขาย1-9-ทรัพย์.xlsx',
    'excel_statement': 'data/inputs/20250319195146_merged_manual.xlsx',
    'output_dir': 'data/output',
    'matching_credit_days': 30,
    'matching_sale_tolerance': 1000.0,
    'matching_purchase_tolerance': 50.0,
}

# Define the output file paths based on CONFIG['output_dir']
OUTPUT_FILES = {
    'transaction_matches': os.path.join(CONFIG['output_dir'], 'รายงานสรุปผลการจับคู่รายการบัญชี.csv'),
    'sale_status': os.path.join(CONFIG['output_dir'], 'รายงานสถานะใบกำกับภาษีขาย.csv'),
    'purchase_status': os.path.join(CONFIG['output_dir'], 'รายงานสถานะใบกำกับภาษีซื้อ.csv'),
    'withholding_status': os.path.join(CONFIG['output_dir'], 'รายงานสถานะรายการภาษีหัก ณ ที่จ่าย.csv'), 
}


EXPECTED_COLUMN_MAPPINGS = {
    # report_name: {
    #     column_name_en: 'column_name_th',
    #     ...
    # },
    # ...
    'purchase_tax_report': {
        'order_number': 'ลำดับ',
        'date_of_purchase_invoice': 'วัน/เดือน/ปี',
        'purchase_invoice_tax_number': 'เลขที่ใบกำกับภาษี',
        'purchase_invoice_id': 'เลขที่เอกสาร',
        'company_name': 'ชื่อผู้ซื้อสินค้า/ผู้รับบริการ', 
        'company_tax_id': 'เลขประจำตัวผู้เสียภาษี',
        'product_value': 'มูลค่าสินค้า',
        'vat': 'ภาษีมูลค่าเพิ่ม',
        'total_amount': 'จำนวนเงิน'
    },
    'sale_tax_report': {
        'order_number': 'ลำดับ',
        'date_of_sale_invoice': 'วัน/เดือน/ปี',
        'sale_invoice_tax_number': 'เลขที่ใบกำกับภาษี',
        'company_name': 'ชื่อผู้ซื้อสินค้า/ผู้รับบริการ',
        'company_tax_id': 'เลขประจำตัวผู้เสียภาษี',
        'product_value': 'มูลค่าสินค้า',
        'vat': 'ภาษีมูลค่าเพิ่ม',
        'total_amount': 'จำนวนเงิน',
        'withholding_tax': 'หัก 3%',
        'net_amount': 'คงเหลือ',
        'matched': 'จับคู่แล้ว', # Matched status mapping
        'days_outstanding': 'จำนวนวันที่ค้างชำระ',
    },
    'withholding_tax_report': {
        'paid_date': 'ว/ด/ป',
        'company_name': 'ชื่อผู้หักภาษี',
        'tax_id': 'เลขประจำตัวผู้เสียภาษี',
        'amount': 'จำนวนเงิน',
        'withholding_tax': 'หัก ณ ที่จ่าย',
        'paid_amount': 'ยอดโอน',
        'days_since_payment': 'จำนวนวันนับจากชำระ',
        'matched': 'จับคู่แล้ว', # Matched status mapping
    },
     'statement': {
        'datetime': 'วันที่และเวลา',
        'amount': 'จำนวนเงิน',
        'isDeposit': 'การฝากเงิน?',
        'balance': 'ยอดคงเหลือ',
        'page': 'หน้าที่'
    },
    'transaction_match_report': {
         'ประเภทรายการ': 'ประเภทรายการ',
         'วันที่ทำรายการ': 'วันที่ทำรายการ',
         'จำนวนเงิน': 'จำนวนเงิน',
         'บริษัท': 'บริษัท',
         'รหัสประจำตัวผู้เสียภาษี': 'รหัสประจำตัวผู้เสียภาษี',
         'เลขที่ใบกำกับภาษี': 'เลขที่ใบกำกับภาษี', # Use for matched invoice numbers
         'วันที่จ่าย': 'วันที่จ่าย', # Use for matched withholding paid dates
         'จำนวนเงินที่จับคู่': 'จำนวนเงินที่จับคู่',
         'ส่วนต่าง': 'ส่วนต่าง',
         'ประเภทการจับคู่': 'ประเภทการจับคู่' # Column indicating how the match was made (Sale, Withholding, Combination)
    }
}

THEME_COLORS = {
    "Dark+ (default dark)": {"bg": "#1E1E1E", "fg": "#D4D4D4", "select_bg": "#264F78", "button": "#333333"},
    "Light+ (default light)": {"bg": "#FFFFFF", "fg": "#000000", "select_bg": "#ADD6FF", "button": "#E0E0E0"},
    "Monokai": {"bg": "#272822", "fg": "#F8F8F2", "select_bg": "#49483E", "button": "#3E3D32"},
    "Solarized Dark": {"bg": "#002B36", "fg": "#839496", "select_bg": "#073642", "button": "#586E75"},
    "Solarized Light": {"bg": "#FDF6E3", "fg": "#657B83", "select_bg": "#EEE8D5", "button": "#93A1A1"},
    "Dracula Official": {"bg": "#282A36", "fg": "#F8F8F2", "select_bg": "#44475A", "button": "#6272A4"},
    "Material Theme": {"bg": "#263238", "fg": "#EEFFFF", "select_bg": "#314549", "button": "#546E7A"},
    "Nord": {"bg": "#2E3440", "fg": "#D8DEE9", "select_bg": "#3B4252", "button": "#434C5E"},
    "One Dark Pro": {"bg": "#282C34", "fg": "#ABB2BF", "select_bg": "#3E4451", "button": "#565C64"},
    "Night Owl": {"bg": "#011627", "fg": "#D6DEEB", "select_bg": "#1D3B53", "button": "#7E57C2"},
    "Shades of Purple": {"bg": "#1E1E3F","fg": "#C7C7C7","select_bg": "#B362FF","button": "#5A00A1"},
    "Atom One Dark": {"bg": "#282C34","fg": "#ABB2BF","select_bg": "#3E4451","button": "#61AFEF"},
    "Cobalt2": {"bg": "#193549","fg": "#FFFFFF","select_bg": "#003B4F","button": "#FF9D00"},
    "Material Palenight": {"bg": "#292D3E","fg": "#A6ACCD","select_bg": "#3E4451","button": "#82AAFF"},
    "Rosé Pine": {"bg": "#191724","fg": "#E0DEF4","select_bg": "#403D52","button": "#EBBCBA"},
    "Tokyo Night": {"bg": "#1A1B26","fg": "#C0CAF5","select_bg": "#33467C","button": "#7AA2F7"},
    "Winter is Coming": {"bg": "#1E1E1E","fg": "#DCDCDC","select_bg": "#264F78","button": "#007ACC"},
    "One Monokai": {"bg": "#222430","fg": "#ABB2BF","select_bg": "#3E4451","button": "#61AFEF"},
    "Bluloco Light": {"bg": "#F5F5F5","fg": "#4D4D4C","select_bg": "#D6D6D6","button": "#A1B56C"}
}