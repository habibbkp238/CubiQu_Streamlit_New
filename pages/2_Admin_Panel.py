import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

from utils.github_utils import read_file_from_github, upload_file_to_github

st.set_page_config(page_title="Admin Panel", page_icon="⚙️", layout="wide")

if not st.session_state.get("logged_in", False):
    st.warning("Silakan login dari halaman utama.")
    st.stop()

if st.session_state.get("role") != "admin":
    st.error("Akses Ditolak. Halaman ini hanya untuk Admin.")
    st.stop()

st.title("⚙️ Admin Panel - Master Data")

# --- Utilities ---
def save_master_data(df, filepath, success_msg):
    with st.spinner("Menyimpan ke GitHub..."):
        if upload_file_to_github(filepath, df, f"Update {filepath}"):
            read_file_from_github.clear()
            st.success(success_msg)

def render_master_editor(filepath, title, expected_cols):
    st.subheader(title)
    df = read_file_from_github(filepath)
    if df.empty:
        st.warning(f"Data {filepath} kosong atau gagal dimuat.")
    else:
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"editor_{filepath}")
        col1, col2 = st.columns([2, 8])
        with col1:
            if st.button("💾 Simpan Perubahan", key=f"save_{filepath}"):
                save_master_data(edited_df, filepath, f"{title} berhasil diperbarui.")
        
        with col2:
            import io
            # Prepare template byte
            template_df = pd.DataFrame(columns=expected_cols)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                template_df.to_excel(writer, index=False, sheet_name='Sheet1')
            st.download_button(
                label=f"⬇️ Download Template {title}",
                data=output.getvalue(),
                file_name=f"Template_{title.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"dl_{filepath}"
            )
            
            uploaded_file = st.file_uploader(f"📤 Upload File Baru ({title})", type=["xlsx"], key=f"up_{filepath}")
            if uploaded_file:
                try:
                    df_up = pd.read_excel(uploaded_file)
                    missing_cols = [c for c in expected_cols if c not in df_up.columns]
                    if missing_cols:
                        st.error(f"❌ Validasi Gagal: Kolom wajib berikut tidak ditemukan di file Excel Anda: {', '.join(missing_cols)}")
                    else:
                        st.success("✅ Validasi Kolom Berhasil!")
                        st.write("Preview:")
                        st.dataframe(df_up.head())
                        if st.button(f"Gantikan {title} dengan file ini", key=f"rep_{filepath}"):
                            save_master_data(df_up, filepath, f"{title} berhasil diganti dengan file baru.")
                            st.rerun()
                except Exception as e:
                    st.error(f"Gagal membaca file: {e}")

tabs = st.tabs(["📦 Master Produk", "🚛 Master Armada", "👥 Master Customer x Armada", "📈 Histori Penjualan", "📋 History Report Log"])

with tabs[0]:
    render_master_editor("data/master_produk.xlsx", "Master Produk", ["Item_Name", "Category", "Length", "Height", "Width", "Volume", "Weight", "is_active"])

with tabs[1]:
    render_master_editor("data/master_armada.xlsx", "Master Armada", ["Jenis_Armada", "Length_cm", "Width_cm", "Height_cm", "Max_Volume_m3", "Max_Tonase_Kg", "Safety_Factor", "is_active"])

with tabs[2]:
    render_master_editor("data/master_customer_armada.xlsx", "Master Customer x Armada", ["Cust_ID", "Cust_Name", "Ship_To_Location", "Company", "Max_Armada", "is_active"])

with tabs[3]:
    st.subheader("Histori Penjualan")
    df_histori = read_file_from_github("data/histori_penjualan.xlsx")
    if not df_histori.empty:
        try:
            df_histori['Date'] = pd.to_datetime(df_histori['Date'])
            three_months_ago = pd.Timestamp.now() - pd.DateOffset(months=3)
            recent_hist = df_histori[df_histori['Date'] >= three_months_ago]
            
            if not recent_hist.empty:
                top_10 = recent_hist.groupby('Item_Name')['Qty'].sum().nlargest(10).reset_index()
                fig = px.bar(top_10, x='Item_Name', y='Qty', title="Top 10 SKU Terlaris (3 Bulan Terakhir)", text_auto=True)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Tidak ada data penjualan dalam 3 bulan terakhir untuk ditampilkan di chart.")
        except Exception as e:
            st.warning("Gagal membuat chart, pastikan format Date sesuai (YYYY-MM-DD).")
            
    render_master_editor("data/histori_penjualan.xlsx", "Data Histori Penjualan", ["Date", "Cust_ID", "Ship_To_Location", "Item_Name", "Qty"])

with tabs[4]:
    st.subheader("History Report Log")
    try:
        config = st.secrets.get("gsheets")
        if config and config.get("spreadsheet_id") != "YOUR_GOOGLE_SHEET_ID" and config.get("credentials_json"):
            creds_dict = json.loads(config["credentials_json"])
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            
            sheet = client.open_by_key(config["spreadsheet_id"]).worksheet("report_log")
            records = sheet.get_all_records()
            
            if records:
                df_log = pd.DataFrame(records)
                st.write(f"Total Reports: {len(df_log)}")
                st.write(f"Unique Users: {df_log['Nama'].nunique() if 'Nama' in df_log.columns else 0}")
                st.dataframe(df_log, use_container_width=True)
            else:
                st.info("Log masih kosong.")
        else:
            st.info("Google Sheets belum dikonfigurasi sepenuhnya di secrets.toml.")
    except Exception as e:
        st.error(f"Gagal memuat log dari Google Sheets: {e}")
