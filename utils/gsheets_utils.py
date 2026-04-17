import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

def append_report_log(nama, jabatan, company, filename, timestamp, armada_1, armada_2, vol_pct_1, weight_pct_1, vol_pct_2, weight_pct_2):
    try:
        config = st.secrets.get("gsheets")
        if not config:
            st.warning("Google Sheets config is missing.")
            return False
            
        spreadsheet_id = config.get("spreadsheet_id")
        creds_json_str = config.get("credentials_json")
        
        if spreadsheet_id == "YOUR_GOOGLE_SHEET_ID" or not creds_json_str:
            # st.warning("Report berhasil didownload namun gagal tercatat di log (development mode).")
            return False
            
        creds_dict = json.loads(creds_json_str)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_key(spreadsheet_id).worksheet("report_log")
        
        row = [
            timestamp, 
            nama, 
            jabatan, 
            company, 
            filename, 
            armada_1, 
            armada_2, 
            vol_pct_1, 
            weight_pct_1, 
            vol_pct_2, 
            weight_pct_2
        ]
        
        sheet.append_row(row)
        return True
    except Exception as e:
        st.warning("Report berhasil didownload namun gagal tercatat di log.")
        return False
