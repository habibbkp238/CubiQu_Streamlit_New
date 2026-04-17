import pandas as pd
from io import BytesIO
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment

def generate_excel_report(nama, jabatan, company, cust_info, armada_1_type, armada_2_type, 
                          vol_1, wgt_1, vol_2, wgt_2, status, items_1, items_2, reco_items):
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Summary
        summary_data = [
            ["Tanggal & Waktu", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["", ""],
            ["Dibuat oleh", ""],
            ["Nama", nama],
            ["Jabatan", jabatan],
            ["Company", company],
            ["", ""],
            ["Customer Info", ""],
            ["Company", cust_info.get("Company", "")],
            ["Cust_Name", cust_info.get("Cust_Name", "")],
            ["Ship-To-Name", cust_info.get("Ship_to_Name", "")],
            ["", ""],
            ["Armada Digunakan", ""],
            ["Armada 1", armada_1_type],
            ["Armada 2", armada_2_type if armada_2_type else "-"],
            ["", ""],
            ["Penggunaan Armada 1", ""],
            ["Volume Terpakai", f"{vol_1:.2f}%"],
            ["Berat Terpakai", f"{wgt_1:.2f}%"],
            ["", ""],
            ["Penggunaan Armada 2", ""] if armada_2_type else ["", ""],
            ["Volume Terpakai", f"{vol_2:.2f}%"] if armada_2_type else ["", ""],
            ["Berat Terpakai", f"{wgt_2:.2f}%"] if armada_2_type else ["", ""],
            ["", ""],
            ["Status", status]
        ]
        
        df_summary = pd.DataFrame(summary_data, columns=["Parameter", "Value"])
        df_summary.to_excel(writer, sheet_name="Summary", index=False)
        
        # Sheet 2: Detail Barang Armada 1
        df_items_1 = pd.DataFrame(items_1)
        if not df_items_1.empty:
            df_items_1['Total Vol'] = df_items_1['Qty'] * df_items_1['Volume']
            df_items_1['Total Weight'] = df_items_1['Qty'] * df_items_1['Weight']
            cols = ['Item_Name', 'Qty', 'Volume', 'Total Vol', 'Weight', 'Total Weight']
            df_items_1[cols].to_excel(writer, sheet_name="Detail Barang Armada 1", index=False)
            
        # Sheet 3: Detail Barang Armada 2
        if armada_2_type and items_2:
            df_items_2 = pd.DataFrame(items_2)
            if not df_items_2.empty:
                df_items_2['Total Vol'] = df_items_2['Qty'] * df_items_2['Volume']
                df_items_2['Total Weight'] = df_items_2['Qty'] * df_items_2['Weight']
                cols = ['Item_Name', 'Qty', 'Volume', 'Total Vol', 'Weight', 'Total Weight']
                df_items_2[cols].to_excel(writer, sheet_name="Detail Barang Armada 2", index=False)
                
        # Sheet 4: Rekomendasi Item
        if reco_items is not None and not reco_items.empty:
            reco_export = reco_items[['Item_Name', 'Avg Qty/Bulan', 'Volume/Unit', 'Weight/Unit']]
            reco_export.to_excel(writer, sheet_name="Rekomendasi Item", index=False)

    return output.getvalue()

def generate_download_template(company_products):
    """
    Generate Excel template for uploading items.
    company_products: List of product names for validation
    """
    output = BytesIO()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Template"
    
    # Headers
    sheet["A1"] = "Item_Name"
    sheet["B1"] = "Qty"
    
    # Data Validation for Item_Name
    dv = openpyxl.worksheet.datavalidation.DataValidation(type="list", formula1=f'"{",".join(company_products)}"', allow_blank=True)
    sheet.add_data_validation(dv)
    dv.add("A2:A100")
    
    workbook.save(output)
    return output.getvalue()
