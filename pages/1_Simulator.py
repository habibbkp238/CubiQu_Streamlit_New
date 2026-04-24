import streamlit as st
import pandas as pd
from datetime import datetime
import os

from utils.github_utils import read_file_from_github, upload_file_to_github
from utils.gsheets_utils import append_report_log
from utils.recommendation import get_recommendations
from utils.report_generator import generate_excel_report, generate_download_template

# ── Callbacks ──────────────────────────────────────────────────
def update_item_qty(item_name, add_qty):
    for j, item in enumerate(st.session_state["item_list"]):
        if item["Item_Name"] == item_name:
            new_val = int(item["Qty"] + add_qty)
            item["Qty"] = new_val
            st.session_state[f"item_qty_{j}"] = new_val
            break

# ── Page Config ────────────────────────────────────────────────
st.set_page_config(page_title="Simulator – CubiQu", page_icon="🚛", layout="wide")

def load_css():
    if os.path.exists("utils/style.css"):
        with open("utils/style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

if not st.session_state.get("logged_in", False):
    st.warning("⚠️ Silakan login dari halaman utama terlebih dahulu.")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    st.markdown(f"""
        <div class="sidebar-user-card">
            <div class="user-name">👤 {st.session_state['username']}</div>
            <div class="user-role">{st.session_state['role'].capitalize()}</div>
        </div>
    """, unsafe_allow_html=True)

# ── Init State ─────────────────────────────────────────────────
for k, v in {"selected_company": None, "selected_cust_id": None,
             "selected_cust_name": None, "selected_shipto": None,
             "selected_armada": None, "item_list": [], "report_generated": False}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Load Data ──────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_all_data():
    df_produk  = read_file_from_github("data/master_produk.xlsx")
    df_armada  = read_file_from_github("data/master_armada.xlsx")
    df_cust    = read_file_from_github("data/master_customer_armada.xlsx")
    df_histori = read_file_from_github("data/histori_penjualan.xlsx")
    return df_produk, df_armada, df_cust, df_histori

try:
    with st.spinner("Memuat master data..."):
        df_produk, df_armada, df_cust, df_histori = load_all_data()
except Exception as e:
    st.error(f"Gagal memuat master data: {e}")
    st.stop()

# ── Page Hero ──────────────────────────────────────────────────
st.markdown("""
    <div class="page-hero">
        <h1>🚛 Simulator Muat Armada</h1>
        <p>Rencanakan muatan secara efisien — real-time volume, tonase & optimasi kapasitas.</p>
    </div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# STEP 1 — PILIH PELANGGAN
# ══════════════════════════════════════════════════════════════
st.markdown("""<div class="step-section"><h4>Step 1 · Pilih Pelanggan</h4>
    <span>Tentukan Company, Customer, dan lokasi Ship-To.</span></div>""", unsafe_allow_html=True)

active_cust = df_cust[df_cust['is_active'] == True]
companies   = active_cust['Company'].unique().tolist()

col1, col2, col3 = st.columns(3)
with col1:
    selected_company = st.selectbox(
        "Company",
        options=companies,
        index=companies.index(st.session_state["selected_company"]) if st.session_state["selected_company"] in companies else 0
    )
    if selected_company != st.session_state["selected_company"]:
        st.session_state["selected_company"]  = selected_company
        st.session_state["selected_cust_name"] = None
        st.session_state["selected_shipto"]    = None

cust_by_comp = active_cust[active_cust['Company'] == selected_company]
cust_names   = cust_by_comp['Cust_Name'].unique().tolist()

with col2:
    idx_cust = cust_names.index(st.session_state["selected_cust_name"]) if st.session_state["selected_cust_name"] in cust_names else 0
    selected_cust_name = st.selectbox("Customer", options=cust_names, index=idx_cust)
    if selected_cust_name != st.session_state["selected_cust_name"]:
        st.session_state["selected_cust_name"] = selected_cust_name
        st.session_state["selected_shipto"]    = None

shipto_by_cust = cust_by_comp[cust_by_comp['Cust_Name'] == selected_cust_name]
shiptos        = shipto_by_cust['Ship_To_Location'].unique().tolist()

with col3:
    idx_shipto = shiptos.index(st.session_state["selected_shipto"]) if st.session_state["selected_shipto"] in shiptos else 0
    selected_shipto = st.selectbox("Ship-To Location", options=shiptos, index=idx_shipto)
    if selected_shipto != st.session_state["selected_shipto"]:
        st.session_state["selected_shipto"]  = selected_shipto
        st.session_state["selected_armada"] = None

if not (selected_company and selected_cust_name and selected_shipto):
    st.info("Pilih pelanggan terlebih dahulu untuk melanjutkan.")
    st.stop()

cust_info = shipto_by_cust[shipto_by_cust['Ship_To_Location'] == selected_shipto].iloc[0]
st.session_state["selected_cust_id"] = cust_info['Cust_ID']
max_armada = cust_info['Max_Armada']

st.markdown(f"""
    <div class="info-card">
        <div class="info-card-item"><div class="label">Cust ID</div><div class="value">{cust_info['Cust_ID']}</div></div>
        <div class="info-card-item"><div class="label">Customer</div><div class="value">{selected_cust_name}</div></div>
        <div class="info-card-item"><div class="label">Ship-To</div><div class="value">{selected_shipto}</div></div>
        <div class="info-card-item"><div class="label">Max Armada</div><div class="value">{max_armada}</div></div>
    </div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# STEP 2 — PILIH ARMADA
# ══════════════════════════════════════════════════════════════
st.markdown("""<div class="step-section"><h4>Step 2 · Pilih Jenis Armada</h4>
    <span>Daftar armada difilter otomatis berdasarkan aturan kapasitas pelanggan.</span></div>""", unsafe_allow_html=True)

df_armada_sorted   = df_armada.sort_values('Max_Volume_m3').copy()
dynamic_order      = df_armada_sorted['Jenis_Armada'].tolist()
dynamic_order_clean = [x.strip().lower() for x in dynamic_order]
max_armada_clean   = str(max_armada).strip().lower()

if max_armada_clean == "container 20":
    allowed_list_clean = ["container 20"]
else:
    try:
        max_idx = dynamic_order_clean.index(max_armada_clean)
        allowed_list_clean = [x for x in dynamic_order_clean[:max_idx+1] if x != "container 20"]
    except ValueError:
        allowed_list_clean = [x for x in dynamic_order_clean if x != "container 20"]

av_armadas = [name for name in dynamic_order if name.strip().lower() in allowed_list_clean]
idx_armada = len(av_armadas) - 1 if av_armadas else 0
if st.session_state.get("selected_armada") in av_armadas:
    idx_armada = av_armadas.index(st.session_state["selected_armada"])

selected_armada = st.selectbox("Pilih Jenis Armada", options=av_armadas, index=idx_armada)
st.session_state["selected_armada"] = selected_armada

armada_specs = df_armada[df_armada['Jenis_Armada'] == selected_armada].iloc[0]
eff_vol = armada_specs['Max_Volume_m3'] * armada_specs['Safety_Factor']
eff_wgt = armada_specs['Max_Tonase_Kg'] * armada_specs['Safety_Factor']

st.markdown(f"""
    <div class="info-card">
        <div class="info-card-item"><div class="label">Armada</div><div class="value">{selected_armada}</div></div>
        <div class="info-card-item"><div class="label">Efektif Volume</div><div class="value">{eff_vol:.2f} m³</div></div>
        <div class="info-card-item"><div class="label">Efektif Tonase</div><div class="value">{eff_wgt:,.0f} kg</div></div>
        <div class="info-card-item"><div class="label">Dimensi (P×T×L)</div><div class="value">{armada_specs['Length_cm']}×{armada_specs['Height_cm']}×{armada_specs['Width_cm']} cm</div></div>
        <div class="info-card-item"><div class="label">Safety Factor</div><div class="value">{armada_specs['Safety_Factor']*100:.0f}%</div></div>
    </div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# STEP 3 — INPUT BARANG
# ══════════════════════════════════════════════════════════════
st.markdown("""<div class="step-section"><h4>Step 3 · Input Barang</h4>
    <span>Tambah item secara manual atau upload file Excel.</span></div>""", unsafe_allow_html=True)

active_products = df_produk[(df_produk['is_active'] == True) & (df_produk['Company'] == selected_company)]
product_names   = active_products['Item_Name'].tolist()

tab1, tab2 = st.tabs(["✏️ Input Manual", "📤 Upload Excel"])

with tab1:
    if st.button("➕ Tambah Baris Item", use_container_width=False):
        st.session_state["item_list"].append({"Item_Name": product_names[0] if product_names else "", "Qty": 1})
        st.rerun()

    for i, item in enumerate(st.session_state["item_list"]):
        c1, c2, c3 = st.columns([4, 1, 1])
        with c1:
            prod_idx = product_names.index(item["Item_Name"]) if item["Item_Name"] in product_names else 0
            new_name = st.selectbox(f"Item #{i+1}", options=product_names, index=prod_idx, key=f"item_name_{i}", label_visibility="collapsed")
        with c2:
            new_qty = st.number_input("Qty", min_value=1, value=int(item["Qty"]), key=f"item_qty_{i}", label_visibility="collapsed")
        with c3:
            if st.button("🗑️", key=f"del_{i}", help="Hapus item ini"):
                st.session_state["item_list"].pop(i)
                st.rerun()
        st.session_state["item_list"][i]["Item_Name"] = new_name
        st.session_state["item_list"][i]["Qty"]       = new_qty

with tab2:
    col_dl, col_ul = st.columns(2)
    with col_dl:
        if product_names:
            st.download_button(
                label="📥 Download Template Excel",
                data=generate_download_template(product_names),
                file_name="template_input_barang.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    with col_ul:
        uploaded_file = st.file_uploader("Upload file Excel", type=["xlsx"], label_visibility="collapsed")
        if uploaded_file:
            try:
                df_up = pd.read_excel(uploaded_file)
                if 'Item_Name' not in df_up.columns or 'Qty' not in df_up.columns:
                    st.error("File harus memiliki kolom 'Item_Name' dan 'Qty'.")
                else:
                    valid_items = [{"Item_Name": r['Item_Name'], "Qty": int(r['Qty'])}
                                   for _, r in df_up.iterrows() if pd.notna(r['Item_Name']) and r['Item_Name'] in product_names]
                    st.write(f"✅ Ditemukan **{len(valid_items)}** item valid.")
                    if st.button("Konfirmasi & Gunakan Data Ini"):
                        st.session_state["item_list"] = valid_items
                        st.rerun()
            except Exception as e:
                st.error(f"Gagal membaca file: {e}")

# ── Enrich Items ───────────────────────────────────────────────
enriched_items = []
total_vol = 0.0
total_wgt = 0.0
for it in st.session_state["item_list"]:
    prod_row = active_products[active_products['Item_Name'] == it['Item_Name']]
    if not prod_row.empty:
        p = prod_row.iloc[0]
        enriched_items.append({"Item_Name": p['Item_Name'], "Qty": it['Qty'],
                                "Volume": p['Volume'], "Weight": p['Weight'],
                                "Length": p['Length'], "Height": p['Height'], "Width": p['Width']})
        total_vol += p['Volume'] * it['Qty']
        total_wgt += p['Weight'] * it['Qty']

# ══════════════════════════════════════════════════════════════
# STEP 4 — STATUS KAPASITAS
# ══════════════════════════════════════════════════════════════
st.markdown("""<div class="step-section"><h4>Step 4 · Status Kapasitas</h4>
    <span>Kalkulasi real-time berdasarkan item yang dipilih.</span></div>""", unsafe_allow_html=True)

if not enriched_items:
    st.info("💡 Tambahkan barang di Step 3 untuk melihat status kapasitas.")
    st.stop()

pct_vol    = (total_vol / eff_vol) * 100
pct_wgt    = (total_wgt / eff_wgt) * 100
needs_split = pct_vol > 100 or pct_wgt > 100

def _bar_color(pct):
    if pct > 100: return "#ef4444"
    if pct >= 80: return "#f59e0b"
    return "#10b981"

def _card_class(pct):
    if pct > 100: return "over"
    if pct >= 80: return "warn"
    return "ok"

bar_w_vol = min(pct_vol, 100)
bar_w_wgt = min(pct_wgt, 100)

m1, m2, m3 = st.columns(3)
with m1:
    st.markdown(f"""
        <div class="metric-card {_card_class(pct_vol)}">
            <div class="mc-label">📦 Volume Terpakai</div>
            <div class="mc-value">{pct_vol:.1f}%</div>
            <div class="mc-sub">{total_vol:.2f} m³ dari {eff_vol:.2f} m³</div>
            <div class="mc-bar-bg"><div class="mc-bar-fill" style="width:{bar_w_vol}%; background:{_bar_color(pct_vol)};"></div></div>
        </div>
    """, unsafe_allow_html=True)
with m2:
    st.markdown(f"""
        <div class="metric-card {_card_class(pct_wgt)}">
            <div class="mc-label">⚖️ Tonase Terpakai</div>
            <div class="mc-value">{pct_wgt:.1f}%</div>
            <div class="mc-sub">{total_wgt:,.0f} kg dari {eff_wgt:,.0f} kg</div>
            <div class="mc-bar-bg"><div class="mc-bar-fill" style="width:{bar_w_wgt}%; background:{_bar_color(pct_wgt)};"></div></div>
        </div>
    """, unsafe_allow_html=True)
with m3:
    if needs_split:
        st.markdown("""
            <div class="metric-card over">
                <div class="mc-label">🚨 Status Muatan</div>
                <div class="mc-value">OVERLOAD</div>
                <div class="mc-sub">Kurangi jumlah item atau ganti armada yang lebih besar</div>
            </div>
        """, unsafe_allow_html=True)
    elif pct_vol >= 99.0 or pct_wgt >= 99.0:
        st.markdown(f"""
            <div class="metric-card ok">
                <div class="mc-label">✅ Status Muatan</div>
                <div class="mc-value">IDEAL</div>
                <div class="mc-sub">Kapasitas sudah dimanfaatkan secara optimal</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="metric-card warn">
                <div class="mc-label">⚠️ Status Muatan</div>
                <div class="mc-value">BELUM IDEAL</div>
                <div class="mc-sub">Sisa: {eff_vol-total_vol:.2f} m³ · {eff_wgt-total_wgt:,.0f} kg — optimalkan di Step 5</div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# STEP 5 — OPTIMALKAN MUATAN (only if not overload)
# ══════════════════════════════════════════════════════════════
if not needs_split and (pct_vol < 99.9 or pct_wgt < 99.9):
    st.markdown("""<div class="step-section"><h4>Step 5 · Optimalkan Muatan</h4>
        <span>Tambah lebih banyak dari item yang sudah ada untuk mendekati 100% kapasitas.</span></div>""", unsafe_allow_html=True)

    sisa_v = eff_vol - total_vol
    sisa_w = eff_wgt - total_wgt

    seen, unique_items = set(), []
    for it in enriched_items:
        if it['Item_Name'] not in seen:
            unique_items.append(it)
            seen.add(it['Item_Name'])

    has_suggestion = False
    for idx, it in enumerate(unique_items):
        add_qty = int(min(
            sisa_v / it['Volume'] if it['Volume'] > 0 else float('inf'),
            sisa_w / it['Weight'] if it['Weight'] > 0 else float('inf')
        ))
        if add_qty > 0:
            has_suggestion = True
            c1, c2, c3 = st.columns([5, 2, 2])
            with c1:
                st.markdown(f"""
                    <div style="padding: 0.5rem 0;">
                        <div class="card-item-name">{it['Item_Name']}</div>
                        <div class="card-item-sub">Vol/Karton: {it['Volume']:.4f} m³ &nbsp;|&nbsp; Berat/Karton: {it['Weight']:.2f} kg</div>
                    </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                    <div style="padding:0.5rem 0; text-align:center;">
                        <div class="card-item-sub">Bisa ditambah</div>
                        <span class="badge badge-green">+{add_qty} Karton</span>
                    </div>
                """, unsafe_allow_html=True)
            with c3:
                st.markdown("<br>", unsafe_allow_html=True)
                st.button(f"Tambah {add_qty} Karton",
                          key=f"opt_{it['Item_Name']}_{idx}",
                          on_click=update_item_qty,
                          args=(it['Item_Name'], add_qty),
                          use_container_width=True)
            st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    if not has_suggestion:
        st.info("Kapasitas sudah optimal — tidak ada penambahan yang memungkinkan.")

elif needs_split:
    st.markdown("""
        <div class="status-banner over">
            🚨 Muatan OVERLOAD — Kurangi jumlah item atau pilih armada yang lebih besar.
        </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# STEP 6 — REKOMENDASI ITEM BARU
# ══════════════════════════════════════════════════════════════
if not needs_split and pct_vol < 100 and pct_wgt < 100:
    st.markdown("""<div class="step-section"><h4>Step 6 · Rekomendasi Item Baru</h4>
        <span>Item yang sering dipesan pelanggan ini tapi belum ada di daftar muat.</span></div>""", unsafe_allow_html=True)

    reco_df, reco_type = get_recommendations(df_histori, df_produk, selected_company,
                                             cust_info['Cust_ID'], selected_shipto, enriched_items)
    if reco_df.empty:
        st.info("Tidak ada rekomendasi yang tersedia berdasarkan histori transaksi.")
    else:
        st.markdown(f"<span class='badge badge-blue'>Sumber: {reco_type}</span><br><br>", unsafe_allow_html=True)

        sisa_v = eff_vol - total_vol
        sisa_w = eff_wgt - total_wgt

        for idx, row in reco_df.iterrows():
            add_v = row['Volume/Unit'] * row['Avg Qty/Bulan']
            add_w = row['Weight/Unit'] * row['Avg Qty/Bulan']
            disabled_avg = bool((total_vol + add_v > eff_vol) or (total_wgt + add_w > eff_wgt))

            max_qty = int(min(
                sisa_v / row['Volume/Unit'] if row['Volume/Unit'] > 0 else float('inf'),
                sisa_w / row['Weight/Unit'] if row['Weight/Unit'] > 0 else float('inf')
            ))

            c1, c2, c3, c4 = st.columns([4, 2, 2, 2])
            with c1:
                st.markdown(f"""
                    <div style="padding:0.4rem 0;">
                        <div class="card-item-name">{row['Item_Name']}</div>
                        <div class="card-item-sub">Vol: {row['Volume/Unit']:.4f} m³ &nbsp;|&nbsp; Berat: {row['Weight/Unit']:.2f} kg</div>
                    </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                    <div style="padding:0.4rem 0; text-align:center;">
                        <div class="card-item-sub">Rata-rata</div>
                        <span class="badge badge-blue">{row['Avg Qty/Bulan']} Karton</span>
                    </div>
                """, unsafe_allow_html=True)
            with c3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(f"Tambah {row['Avg Qty/Bulan']}", key=f"reco_avg_{idx}",
                             disabled=disabled_avg, use_container_width=True):
                    st.session_state["item_list"].append({"Item_Name": row['Item_Name'], "Qty": row['Avg Qty/Bulan']})
                    st.rerun()
            with c4:
                st.markdown("<br>", unsafe_allow_html=True)
                if max_qty > 0:
                    if st.button(f"Tambah {max_qty} (Penuh)", key=f"reco_full_{idx}", use_container_width=True):
                        st.session_state["item_list"].append({"Item_Name": row['Item_Name'], "Qty": max_qty})
                        st.rerun()
                else:
                    st.button("⚠️ Kapasitas Penuh", key=f"reco_full_{idx}", disabled=True, use_container_width=True)

            st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# STEP 7 — EXPORT REPORT
# ══════════════════════════════════════════════════════════════
st.markdown("""<div class="step-section"><h4>Step 7 · Export Report</h4>
    <span>Generate laporan Excel untuk arsip dan dokumentasi pengiriman.</span></div>""", unsafe_allow_html=True)

with st.expander("📋 Konfigurasi & Generate Report", expanded=False):
    with st.form("export_form"):
        st.markdown("<p style='color:#64748b; margin-bottom:1rem;'>Isi detail laporan sebelum men-download.</p>", unsafe_allow_html=True)
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            rep_nama    = st.text_input("Nama Lengkap", placeholder="Contoh: Budi Santoso")
            rep_jabatan = st.text_input("Jabatan", placeholder="Contoh: Sales Supervisor")
        with col_f2:
            rep_comp = st.text_input("Company", value=selected_company)

        st.write("")
        sub_rep = st.form_submit_button("✅ Generate & Archive Report", use_container_width=True)
        if sub_rep:
            if not rep_nama or not rep_jabatan:
                st.error("Nama Lengkap dan Jabatan wajib diisi.")
            else:
                stat = "Muat" if not needs_split else "Tidak Muat"
                try:
                    reco_df_export, _ = get_recommendations(df_histori, df_produk, rep_comp,
                                                            cust_info['Cust_ID'], selected_shipto, enriched_items)
                except:
                    reco_df_export = pd.DataFrame()

                excel_bytes = generate_excel_report(
                    rep_nama, rep_jabatan, rep_comp, cust_info,
                    selected_armada, None,
                    pct_vol, pct_wgt, 0, 0, stat,
                    enriched_items, [], reco_df_export
                )
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{rep_comp.replace(' ','')}_{rep_nama.replace(' ','')}.xlsx"
                st.session_state["report_bytes"]    = excel_bytes
                st.session_state["report_filename"] = filename

                upload_file_to_github(f"history/{filename}", excel_bytes, f"Added report {filename}")
                append_report_log(rep_nama, rep_jabatan, rep_comp, filename,
                                  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                  selected_armada, "-", pct_vol, pct_wgt, 0, 0)
                st.success("✅ Report berhasil digenerate dan diarsipkan.")

if "report_bytes" in st.session_state:
    st.download_button(
        label="📥 Download Report Excel",
        data=st.session_state["report_bytes"],
        file_name=st.session_state["report_filename"],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
