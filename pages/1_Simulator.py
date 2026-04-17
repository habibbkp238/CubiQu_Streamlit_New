import streamlit as st
import pandas as pd
from datetime import datetime
import io

import sys
import os

from utils.github_utils import read_file_from_github, upload_file_to_github
from utils.gsheets_utils import append_report_log
from utils.packing_engine import run_3d_packing, draw_2d_floor_plan, draw_3d_packing_bin
from utils.recommendation import get_recommendations
from utils.report_generator import generate_excel_report, generate_download_template
from config import ARMADA_ORDER

st.set_page_config(page_title="Simulator Muat Armada", page_icon="🚛", layout="wide")

if not st.session_state.get("logged_in", False):
    st.warning("Silakan login dari halaman utama.")
    st.stop()

# --- Initialize specific state variables if missing ---
def init_page_state():
    defaults = {
        "selected_company": None,
        "selected_cust_id": None,
        "selected_cust_name": None,
        "selected_shipto": None,
        "selected_armada": None,
        "item_list": [],
        "armada1_items": [],
        "armada2_items": [],
        "show_split": False,
        "report_generated": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_page_state()

# --- Load Data ---
@st.cache_data(ttl=300)
def load_all_data():
    df_produk = read_file_from_github("data/master_produk.xlsx")
    df_armada = read_file_from_github("data/master_armada.xlsx")
    df_cust = read_file_from_github("data/master_customer_armada.xlsx")
    df_histori = read_file_from_github("data/histori_penjualan.xlsx")
    return df_produk, df_armada, df_cust, df_histori

try:
    with st.spinner("Memuat Master Data..."):
        df_produk, df_armada, df_cust, df_histori = load_all_data()
except Exception as e:
    st.error(f"Gagal memuat master data: {e}")
    st.stop()

st.title("🚛 Simulator Kalkulator Muat Armada")

# --- STEP 1: CUSTOMER SELECTION ---
st.header("1. Pilih Pelanggan")

col1, col2, col3 = st.columns(3)

with col1:
    active_cust = df_cust[df_cust['is_active'] == True]
    companies = active_cust['Company'].unique().tolist()
    
    selected_company = st.selectbox(
        "Company", 
        options=companies, 
        index=companies.index(st.session_state["selected_company"]) if st.session_state["selected_company"] in companies else 0
    )
    if selected_company != st.session_state["selected_company"]:
        st.session_state["selected_company"] = selected_company
        # Reset downstream selections safely
        st.session_state["selected_cust_name"] = None
        st.session_state["selected_shipto"] = None

with col2:
    cust_by_comp = active_cust[active_cust['Company'] == selected_company]
    cust_names = cust_by_comp['Cust_Name'].unique().tolist()
    
    idx_cust = 0
    if st.session_state["selected_cust_name"] in cust_names:
        idx_cust = cust_names.index(st.session_state["selected_cust_name"])
        
    selected_cust_name = st.selectbox("Customer", options=cust_names, index=idx_cust if cust_names else 0)
    
    if selected_cust_name != st.session_state["selected_cust_name"]:
        st.session_state["selected_cust_name"] = selected_cust_name
        st.session_state["selected_shipto"] = None

with col3:
    shipto_by_cust = cust_by_comp[cust_by_comp['Cust_Name'] == selected_cust_name]
    shiptos = shipto_by_cust['Ship_to_Name'].unique().tolist()
    
    idx_shipto = 0
    if st.session_state["selected_shipto"] in shiptos:
        idx_shipto = shiptos.index(st.session_state["selected_shipto"])
        
    selected_shipto = st.selectbox("Ship-To-Name", options=shiptos, index=idx_shipto if shiptos else 0)
    
    if selected_shipto != st.session_state["selected_shipto"]:
        st.session_state["selected_shipto"] = selected_shipto
        st.session_state["selected_armada"] = None

if not selected_company or not selected_cust_name or not selected_shipto:
    st.info("Pilih pelanggan terlebih dahulu.")
    st.stop()

# Get customer info
cust_info = shipto_by_cust[shipto_by_cust['Ship_to_Name'] == selected_shipto].iloc[0]
st.session_state["selected_cust_id"] = cust_info['Cust_ID']
max_armada = cust_info['Max_Armada']

st.success(f"**Cust ID**: {cust_info['Cust_ID']} | **Max Armada**: {max_armada}")


# --- STEP 2: ARMADA SELECTION ---
st.header("2. Pilih Jenis Armada")

# Filter armada based on Max_Armada
try:
    max_idx = ARMADA_ORDER.index(max_armada)
    allowed_armadas = ARMADA_ORDER[:max_idx+1]
except ValueError:
    allowed_armadas = ARMADA_ORDER

av_armadas = df_armada[df_armada['Jenis_Armada'].isin(allowed_armadas)]['Jenis_Armada'].tolist()

idx_armada = len(av_armadas) - 1 if av_armadas else 0
if st.session_state.get("selected_armada") in av_armadas:
    idx_armada = av_armadas.index(st.session_state["selected_armada"])

selected_armada = st.selectbox("Pilih Jenis Armada", options=av_armadas, index=idx_armada if av_armadas else 0)
st.session_state["selected_armada"] = selected_armada

armada_specs = df_armada[df_armada['Jenis_Armada'] == selected_armada].iloc[0]
eff_vol = armada_specs['Max_Volume_m3'] * armada_specs['Safety_Factor']
eff_wgt = armada_specs['Max_Tonase_Kg'] * armada_specs['Safety_Factor']

st.info(f"**Spesifikasi Efektif**: {eff_vol:.2f} m³ | {eff_wgt:,.0f} kg | Dimensi (LxTxL): {armada_specs['Length_cm']}x{armada_specs['Height_cm']}x{armada_specs['Width_cm']} cm | Safety Factor: {armada_specs['Safety_Factor']*100:.0f}%")


# --- STEP 3: INPUT BARANG ---
st.header("3. Input Barang")

active_products = df_produk[(df_produk['is_active'] == True) & (df_produk['Company'] == selected_company)]
product_names = active_products['Item_Name'].tolist()

tab1, tab2 = st.tabs(["✏️ Input Manual", "📤 Upload Excel"])

with tab1:
    if st.button("+ Tambah Barang"):
        st.session_state["item_list"].append({
            "Item_Name": product_names[0] if product_names else "",
            "Qty": 1
        })
        st.rerun()
        
    for i, item in enumerate(st.session_state["item_list"]):
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            prod_idx = product_names.index(item["Item_Name"]) if item["Item_Name"] in product_names else 0
            new_name = st.selectbox(f"Item #{i+1}", options=product_names, index=prod_idx, key=f"item_name_{i}")
        with c2:
            new_qty = st.number_input(f"Qty", min_value=1, value=int(item["Qty"]), key=f"item_qty_{i}")
        with c3:
            st.write("")
            st.write("")
            if st.button("🗑️", key=f"del_{i}"):
                st.session_state["item_list"].pop(i)
                st.rerun()
                
        st.session_state["item_list"][i]["Item_Name"] = new_name
        st.session_state["item_list"][i]["Qty"] = new_qty

with tab2:
    col_dl, col_ul = st.columns(2)
    with col_dl:
        if product_names:
            template_bytes = generate_download_template(product_names)
            st.download_button(
                label="📥 Download Template",
                data=template_bytes,
                file_name="template_input_barang.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    uploaded_file = st.file_uploader("Upload file Excel input barang", type=["xlsx"])
    if uploaded_file is not None:
        try:
            df_up = pd.read_excel(uploaded_file)
            if 'Item_Name' not in df_up.columns or 'Qty' not in df_up.columns:
                st.error("File harus memiliki kolom 'Item_Name' dan 'Qty'.")
            else:
                valid_items = []
                for idx, row in df_up.iterrows():
                    name = row['Item_Name']
                    qty = row['Qty']
                    if pd.notna(name) and name in product_names:
                        valid_items.append({"Item_Name": name, "Qty": int(qty)})
                
                st.write(f"Ditemukan {len(valid_items)} item valid.")
                if st.button("✅ Konfirmasi & Gunakan Data Ini"):
                    st.session_state["item_list"] = valid_items
                    st.rerun()
        except Exception as e:
            st.error(f"Gagal membaca file: {e}")

# Enrich item details
enriched_items = []
total_vol = 0.0
total_wgt = 0.0

for it in st.session_state["item_list"]:
    prod_row = active_products[active_products['Item_Name'] == it['Item_Name']]
    if not prod_row.empty:
        p = prod_row.iloc[0]
        it_full = {
            "Item_Name": p['Item_Name'],
            "Qty": it['Qty'],
            "Volume": p['Volume'],
            "Weight": p['Weight'],
            "Length": p['Length'],
            "Height": p['Height'],
            "Width": p['Width']
        }
        enriched_items.append(it_full)
        total_vol += (p['Volume'] * it['Qty'])
        total_wgt += (p['Weight'] * it['Qty'])

# --- STEP 4: KALKULASI REAL-TIME ---
st.header("4. Status Kapasitas")

if enriched_items:
    pct_vol = (total_vol / eff_vol) * 100
    pct_wgt = (total_wgt / eff_wgt) * 100
    
    st.write("### Rekapitulasi")
    
    def render_progress(val, limit, label, unit):
        pct = min(val / limit * 100, 100.0)
        c = "green"
        if val / limit >= 1.0:
            c = "red"
        elif val / limit >= 0.8:
            c = "orange"
            
        st.markdown(f"**{label}**: <span style='color:{c}; font-weight:bold;'>{val / limit * 100:.1f}% terpakai</span> ({val:,.2f} {unit} dari {limit:,.2f} {unit})", unsafe_allow_html=True)
        st.progress(pct / 100.0)
        
    render_progress(total_vol, eff_vol, "📦 Volume", "m³")
    render_progress(total_wgt, eff_wgt, "⚖️ Berat", "kg")
    
    # 3D Packing Check
    with st.spinner("Menghitung layout 3D..."):
         pack_res = run_3d_packing(enriched_items, armada_specs)
         
    if not pack_res["success"]:
        st.warning("⚠️ 3D packing tidak dapat dijalankan, menggunakan kalkulasi volume")
    elif pack_res["unfitted"] > 0:
        st.error(f"⚠️ {pack_res['unfitted']} unit tidak muat secara fisik dalam 1 armada.")
    else:
        st.success("✅ Seluruh barang muat secara fisik.")

    if pack_res["success"] and pack_res.get("bin"):
        st.info("💡 **Tips Interaktif**: Grafik 3D di bawah ini bisa diputar ke segala arah, digeser, dan *di-zoom* dengan mouse/layar sentuh Anda. Kotak garis hitam tipis adalah batas ruang dalam truk.")
        fig_3d = draw_3d_packing_bin(pack_res["bin"], armada_specs, "🗺️ Visualisasi 3D Ruang Kargo (Armada Utama)")
        st.plotly_chart(fig_3d, use_container_width=True)

    # --- STEP 5: SPLIT ARMADA ---
    needs_split = (pct_vol > 100 or pct_wgt > 100 or pack_res.get("unfitted", 0) > 0)
    
    if "user_wants_split" not in st.session_state:
        st.session_state["user_wants_split"] = False
    if "armada2_type" not in st.session_state:
        st.session_state["armada2_type"] = None

    if needs_split:
        st.warning("⚠️ Kapasitas armada pertama tidak mencukupi untuk semua barang.")
        
        # Confirmation
        user_wants_split = st.checkbox("Gunakan 2 Armada (Split)?", value=st.session_state["user_wants_split"])
        st.session_state["user_wants_split"] = user_wants_split
        
        if user_wants_split:
            st.session_state["show_split"] = True
        else:
            st.session_state["show_split"] = False
    else:
        st.session_state["show_split"] = False
        st.session_state["user_wants_split"] = False
        st.session_state["armada2_type"] = None

    if not st.session_state.get("show_split"):
        st.session_state["armada1_items"] = enriched_items.copy()
        st.session_state["armada2_items"] = []
        
    if st.session_state.get("show_split"):
        st.header("5. Split Armada (2 Armada)")
        
        armada2_options = df_armada['Jenis_Armada'].tolist()
        idx_a2 = 0
        if st.session_state["armada2_type"] in armada2_options:
            idx_a2 = armada2_options.index(st.session_state["armada2_type"])
            
        armada2_type = st.selectbox("Pilih Jenis Armada 2", options=armada2_options, index=idx_a2)
        if armada2_type != st.session_state["armada2_type"]:
            st.session_state["armada2_type"] = armada2_type
            st.session_state["split_initialized"] = False
            st.rerun()
            
        a2_specs = df_armada[df_armada['Jenis_Armada'] == armada2_type].iloc[0]
        a2_eff_vol = a2_specs['Max_Volume_m3'] * a2_specs['Safety_Factor']
        a2_eff_wgt = a2_specs['Max_Tonase_Kg'] * a2_specs['Safety_Factor']

        # Initial auto distribution if not populated
        if not st.session_state.get("split_initialized", False) or sum([it['Qty'] for it in st.session_state["armada1_items"]]) + sum([it['Qty'] for it in st.session_state["armada2_items"]]) != sum([it['Qty'] for it in enriched_items]):
            st.session_state["armada1_items"] = []
            st.session_state["armada2_items"] = []
            
            # Simple greedy
            sorted_items = sorted(enriched_items, key=lambda x: x['Volume'], reverse=True)
            v1, w1 = 0, 0
            for iit in sorted_items:
                rem_qty = iit['Qty']
                
                while rem_qty > 0:
                    if v1 + iit['Volume'] <= eff_vol and w1 + iit['Weight'] <= eff_wgt:
                        v1 += iit['Volume']
                        w1 += iit['Weight']
                        # Add 1 unit to A1
                        found = False
                        for a1 in st.session_state["armada1_items"]:
                            if a1['Item_Name'] == iit['Item_Name']:
                                a1['Qty'] += 1
                                found = True
                        if not found:
                            new_it = iit.copy()
                            new_it['Qty'] = 1
                            st.session_state["armada1_items"].append(new_it)
                    else:
                        # Add to A2
                        found = False
                        for a2 in st.session_state["armada2_items"]:
                            if a2['Item_Name'] == iit['Item_Name']:
                                a2['Qty'] += 1
                                found = True
                        if not found:
                            new_it = iit.copy()
                            new_it['Qty'] = 1
                            st.session_state["armada2_items"].append(new_it)
                    rem_qty -= 1
            st.session_state["split_initialized"] = True
            
        c_a1, c_a2 = st.columns(2)
        
        def calc_summary(items_list):
            v = sum([i['Volume'] * i['Qty'] for i in items_list])
            w = sum([i['Weight'] * i['Qty'] for i in items_list])
            return v, w
            
        with c_a1:
            st.subheader("🚛 Armada 1")
            v1, w1 = calc_summary(st.session_state["armada1_items"])
            st.write(f"Vol: {v1/eff_vol*100:.1f}% | Berat: {w1/eff_wgt*100:.1f}%")
            
            for idx, iit in enumerate(st.session_state["armada1_items"]):
                c_n, c_b = st.columns([4, 1])
                c_n.write(f"{iit['Item_Name']} (x{iit['Qty']})")
                if c_b.button("→", key=f"mv_r_{idx}"):
                    # Move 1 to A2
                    st.session_state["armada1_items"][idx]['Qty'] -= 1
                    found = False
                    for x in st.session_state["armada2_items"]:
                        if x['Item_Name'] == iit['Item_Name']:
                            x['Qty'] += 1
                            found = True
                    if not found:
                        ni = iit.copy()
                        ni['Qty'] = 1
                        st.session_state["armada2_items"].append(ni)
                    if st.session_state["armada1_items"][idx]['Qty'] == 0:
                        st.session_state["armada1_items"].pop(idx)
                    st.rerun()
            
            fig1 = draw_2d_floor_plan(st.session_state["armada1_items"], armada_specs, "Visualisasi Lantai 2D (Armada 1)")
            st.plotly_chart(fig1, use_container_width=True)
            
            with st.spinner("Menghitung layout 3D Armada 1..."):
                a1_pack_res = run_3d_packing(st.session_state["armada1_items"], armada_specs)
            if a1_pack_res["success"] and a1_pack_res.get("bin"):
                fig1_3d = draw_3d_packing_bin(a1_pack_res["bin"], armada_specs, "Visualisasi 3D Armada 1")
                st.plotly_chart(fig1_3d, use_container_width=True)
            
        with c_a2:
            st.subheader("🚛 Armada 2")
            v2, w2 = calc_summary(st.session_state["armada2_items"])
            st.write(f"Vol: {v2/a2_eff_vol*100:.1f}% | Berat: {w2/a2_eff_wgt*100:.1f}%")
            
            for idx, iit in enumerate(st.session_state["armada2_items"]):
                c_b, c_n = st.columns([1, 4])
                if c_b.button("←", key=f"mv_l_{idx}"):
                    # Move 1 to A1
                    st.session_state["armada2_items"][idx]['Qty'] -= 1
                    found = False
                    for x in st.session_state["armada1_items"]:
                        if x['Item_Name'] == iit['Item_Name']:
                            x['Qty'] += 1
                            found = True
                    if not found:
                        ni = iit.copy()
                        ni['Qty'] = 1
                        st.session_state["armada1_items"].append(ni)
                    if st.session_state["armada2_items"][idx]['Qty'] == 0:
                        st.session_state["armada2_items"].pop(idx)
                    st.rerun()
                c_n.write(f"{iit['Item_Name']} (x{iit['Qty']})")
                
            fig2 = draw_2d_floor_plan(st.session_state["armada2_items"], a2_specs, "Visualisasi Lantai 2D (Armada 2)")
            st.plotly_chart(fig2, use_container_width=True)

            with st.spinner("Menghitung layout 3D Armada 2..."):
                a2_pack_res = run_3d_packing(st.session_state["armada2_items"], a2_specs)
            if a2_pack_res["success"] and a2_pack_res.get("bin"):
                fig2_3d = draw_3d_packing_bin(a2_pack_res["bin"], a2_specs, "Visualisasi 3D Armada 2")
                st.plotly_chart(fig2_3d, use_container_width=True)

    # --- STEP 6: REKOMENDASI ITEM ---
    if not needs_split and pct_vol < 100 and pct_wgt < 100:
        st.header("💡 Rekomendasi Tambahan Item")
        st.write(f"Sisa kapasitas: {eff_vol - total_vol:.2f} m³ volume | {eff_wgt - total_wgt:.2f} kg berat")
        
        reco_df, reco_type = get_recommendations(df_histori, df_produk, cust_info['Cust_ID'], selected_shipto, enriched_items)
        if not reco_df.empty:
            st.info(f"Rekomendasi berdasarkan: **{reco_type}**")
            for idx, row in reco_df.iterrows():
                col_n, col_d, col_b1, col_b2 = st.columns([3, 3, 2, 2])
                col_n.write(row['Item_Name'])
                col_d.write(f"Avg: {row['Avg Qty/Bulan']} | Vol: {row['Volume/Unit']:.4f} | Wgt: {row['Weight/Unit']:.2f}")
                
                # Cek jika ditambahkan apakah akan melebihi kapasitas
                add_v = row['Volume/Unit'] * row['Avg Qty/Bulan']
                add_w = row['Weight/Unit'] * row['Avg Qty/Bulan']
                disabled = bool((total_vol + add_v > eff_vol) or (total_wgt + add_w > eff_wgt))
                
                if col_b1.button(f"+ Tambah ({row['Avg Qty/Bulan']} unit)", key=f"reco_avg_{idx}_{row['Item_Name']}", disabled=disabled):
                    st.session_state["item_list"].append({
                        "Item_Name": row['Item_Name'],
                        "Qty": row['Avg Qty/Bulan']
                    })
                    st.rerun()

                # Hitung max qty yang bisa dimasukkan
                sisa_v = eff_vol - total_vol
                sisa_w = eff_wgt - total_wgt
                max_v_qty = sisa_v / row['Volume/Unit'] if row['Volume/Unit'] > 0 else float('inf')
                max_w_qty = sisa_w / row['Weight/Unit'] if row['Weight/Unit'] > 0 else float('inf')
                max_qty = int(min(max_v_qty, max_w_qty))

                if max_qty > 0:
                    if col_b2.button(f"+ Isi Penuh ({max_qty} unit)", key=f"reco_full_{idx}_{row['Item_Name']}"):
                        st.session_state["item_list"].append({
                            "Item_Name": row['Item_Name'],
                            "Qty": max_qty
                        })
                        st.rerun()
                else:
                    col_b2.write("⚠️ Tidak Muat")

    # --- STEP 7: EXPORT REPORT ---
    st.header("7. Export Report")
    with st.expander("📊 Download Report"):
        with st.form("export_form"):
            rep_nama = st.text_input("Nama Lengkap")
            rep_jabatan = st.text_input("Jabatan")
            rep_comp = st.text_input("Company", value=selected_company)
            
            sub_rep = st.form_submit_button("✅ Generate & Download Report")
            if sub_rep:
                if not rep_nama or not rep_jabatan:
                    st.error("Nama Lengkap dan Jabatan harus diisi.")
                else:
                    if st.session_state["show_split"]:
                        v1, w1 = calc_summary(st.session_state["armada1_items"])
                        v2, w2 = calc_summary(st.session_state["armada2_items"])
                        p_v1, p_w1 = v1/eff_vol*100, w1/eff_wgt*100
                        p_v2, p_w2 = v2/a2_eff_vol*100, w2/a2_eff_wgt*100
                        a2_type = st.session_state["armada2_type"]
                        stat = "Split 2 Armada"
                        i1 = st.session_state["armada1_items"]
                        i2 = st.session_state["armada2_items"]
                    else:
                        p_v1, p_w1 = pct_vol, pct_wgt
                        p_v2, p_w2 = 0, 0
                        a2_type = None
                        stat = "Muat" if (pct_vol <= 100 and pct_wgt <= 100) else "Tidak Muat"
                        i1 = enriched_items
                        i2 = []

                    try:
                        reco_df, _ = get_recommendations(df_histori, df_produk, cust_info['Cust_ID'], selected_shipto, enriched_items)
                    except:
                        reco_df = pd.DataFrame()

                    excel_bytes = generate_excel_report(
                        rep_nama, rep_jabatan, rep_comp, cust_info,
                        selected_armada, a2_type,
                        p_v1, p_w1, p_v2, p_w2, stat,
                        i1, i2, reco_df
                    )
                    
                    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{rep_comp.replace(' ', '')}_{rep_nama.replace(' ', '')}.xlsx"
                    st.session_state["report_bytes"] = excel_bytes
                    st.session_state["report_filename"] = filename
                    
                    # Upload to GitHub
                    upload_file_to_github(f"history/{filename}", excel_bytes, f"Added report {filename}")
                    
                    # Append Log
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    append_report_log(rep_nama, rep_jabatan, rep_comp, filename, ts, selected_armada, a2_type or "-", p_v1, p_w1, p_v2, p_w2)

                    st.success("Report berhasil digenerate dan dikatalogkan! Silakan klik tombol di bawah untuk mendownload.")

        if "report_bytes" in st.session_state:
            st.download_button(
                label="📥 Download Excel",
                data=st.session_state["report_bytes"],
                file_name=st.session_state["report_filename"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
else:
    st.info("Tambahkan barang untuk melihat kalkulasi.")
