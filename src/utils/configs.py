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