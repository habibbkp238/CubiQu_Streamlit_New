import streamlit as st
import os

st.set_page_config(page_title="FAQ – CubiQu", page_icon="❓", layout="wide")

def load_css():
    if os.path.exists("utils/style.css"):
        with open("utils/style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css()

if not st.session_state.get("logged_in", False):
    st.warning("⚠️ Silakan login dari halaman utama.")
    st.stop()

with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    st.markdown(f"""
        <div class="sidebar-user-card">
            <div class="user-name">👤 {st.session_state['username']}</div>
            <div class="user-role">{st.session_state['role'].capitalize()}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("""
    <div class="page-hero">
        <h1>❓ Frequently Asked Questions</h1>
        <p>Pelajari cara kerja CubiQu dan aturan-aturan pemuatan armada.</p>
    </div>
""", unsafe_allow_html=True)

faqs = [
    ("🔒 Apa itu Safety Factor?",
     "Safety Factor adalah persentase kapasitas yang boleh digunakan, ditetapkan per armada di Master Armada. "
     "Misal Safety Factor 90% berarti hanya 90% dari volume & tonase maksimum yang boleh diisi — "
     "sisanya adalah buffer untuk void space antar barang dan toleransi keamanan."),
    ("🚨 Mengapa status OVERLOAD padahal volume belum 100%?",
     "Status OVERLOAD dipicu jika **salah satu** dari Volume ATAU Tonase melebihi kapasitas efektif. "
     "Cek indikator Tonase di panel Status Kapasitas — bisa jadi berat yang melampaui batas meski volume masih ada sisa."),
    ("🚀 Bagaimana cara kerja 'Optimalkan Muatan'?",
     "Fitur ini menghitung sisa kapasitas (volume & berat) lalu membaginya dengan dimensi/berat per karton "
     "dari setiap item yang sudah ada di daftar. Hasilnya adalah jumlah karton tambahan yang bisa masuk "
     "tanpa melampaui 100%. Klik tombol untuk langsung menambahkannya ke daftar."),
    ("💡 Dari mana asal 'Rekomendasi Item Baru'?",
     "Rekomendasi berasal dari histori transaksi pelanggan dalam 180 hari terakhir. "
     "Sistem menyarankan item yang paling sering dibeli tapi belum ada di daftar muat saat ini. "
     "Ada dua pilihan: tambah sesuai rata-rata pesanan, atau isi penuh sisa kapasitas."),
    ("🚛 Kenapa armada tertentu tidak muncul di pilihan?",
     "Daftar armada difilter berdasarkan kolom 'Max_Armada' di Master Customer. "
     "Jika pelanggan di-set 'Engkel', armada yang lebih besar tidak akan muncul. "
     "Admin dapat mengubah ini melalui menu Admin Panel → Master Customer."),
    ("📋 Apakah report tersimpan secara otomatis?",
     "Ya. Saat klik 'Generate & Archive Report', file Excel otomatis diunggah ke folder 'history' di GitHub "
     "dan log-nya dicatat di Google Sheets. Anda bisa melihat semua riwayat laporan di Admin Panel → History Report Log."),
    ("📤 Format Excel apa yang bisa di-upload?",
     "File harus berformat .xlsx dengan minimal dua kolom: **Item_Name** (nama item sesuai Master Produk) "
     "dan **Qty** (jumlah karton). Download template di Step 3 tab Upload Excel untuk memastikan format yang benar."),
    ("⚡ Data tidak terupdate setelah Admin mengubah Master?",
     "Data di-cache selama 5 menit untuk efisiensi. Tunggu 5 menit atau minta Admin "
     "untuk clear cache melalui refresh halaman setelah melakukan perubahan di Admin Panel."),
]

for q, a in faqs:
    with st.expander(q):
        st.markdown(a)

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center; color:#94a3b8; font-size:0.8rem;'>CubiQu Enterprise · PT. Bina Karya Prima · 2025</p>",
    unsafe_allow_html=True
)
