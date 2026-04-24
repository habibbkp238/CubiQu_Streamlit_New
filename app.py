import streamlit as st
import os

st.set_page_config(
    page_title="CubiQu – Smart Load Planning",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS Injection ──────────────────────────────────────────────
def load_css():
    css_path = "utils/style.css"
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# ── Session State ──────────────────────────────────────────────
def init_session_state():
    defaults = {
        "logged_in": False,
        "role": "",
        "username": "",
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

# ── Sidebar (shared) ───────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        
        st.markdown(f"""
            <div class="sidebar-user-card">
                <div class="user-name">👤 {st.session_state['username']}</div>
                <div class="user-role">{st.session_state['role'].capitalize()}</div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# ── Login Page ─────────────────────────────────────────────────
def login():
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        # Logo / Brand area
        st.markdown('<div class="login-logo-area">', unsafe_allow_html=True)
        if os.path.exists("logo.png"):
            logo_col1, logo_col2, logo_col3 = st.columns([1, 3, 1])
            with logo_col2:
                st.image("logo.png", use_container_width=True)
        else:
            st.markdown("<div style='font-size:3rem; text-align:center;'>🚛</div>", unsafe_allow_html=True)

        st.markdown("""
            <h2>CubiQu</h2>
            <p>Smart Load Planning & Optimization</p>
            </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            st.markdown('<p class="login-card-title">Welcome back</p>', unsafe_allow_html=True)
            st.markdown('<p class="login-card-sub">Enter your credentials to continue</p>', unsafe_allow_html=True)
            
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In →", use_container_width=True)

            if submitted:
                users_config = st.secrets.get("users", {})
                user_found = False
                for key, val in users_config.items():
                    if key.endswith("_username") and val == username:
                        prefix = key.replace("_username", "")
                        if users_config.get(f"{prefix}_password") == password:
                            user_found = True
                            st.session_state["logged_in"] = True
                            st.session_state["username"] = username
                            st.session_state["role"] = "admin" if prefix == "admin" else "sales"
                            st.rerun()
                            break
                if not user_found:
                    st.error("⚠️ Username atau password tidak valid.")

        st.markdown('</div>', unsafe_allow_html=True)

        # Footer
        st.markdown(
            "<p style='text-align:center; color:#94a3b8; font-size:0.75rem; margin-top:1.5rem;'>"
            "© 2025 CubiQu · PT. Bina Karya Prima</p>",
            unsafe_allow_html=True
        )

# ── Welcome / Home Dashboard ───────────────────────────────────
def home_dashboard():
    render_sidebar()

    # Hero
    st.markdown(f"""
        <div class="page-hero">
            <h1>🚛 Selamat Datang, {st.session_state['username']}!</h1>
            <p>Gunakan menu di sidebar untuk mengakses Simulator Muat atau Admin Panel.</p>
        </div>
    """, unsafe_allow_html=True)

    # Feature highlights
    st.markdown("""
        <div class="welcome-card">
            <h3 style="margin-top:0;">Apa yang bisa kamu lakukan?</h3>
            <div class="feature-grid">
                <div class="feature-item">
                    <div class="fi-icon">🧮</div>
                    <div class="fi-title">Simulasi Muat</div>
                    <div class="fi-desc">Hitung volume & tonase secara real-time sebelum pengiriman</div>
                </div>
                <div class="feature-item">
                    <div class="fi-icon">💡</div>
                    <div class="fi-title">Rekomendasi Cerdas</div>
                    <div class="fi-desc">Saran tambahan item berdasarkan histori transaksi pelanggan</div>
                </div>
                <div class="feature-item">
                    <div class="fi-icon">🚀</div>
                    <div class="fi-title">Optimalkan Muatan</div>
                    <div class="fi-desc">Isi sisa kapasitas armada secara otomatis hingga 100%</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ── Main ───────────────────────────────────────────────────────
def main():
    init_session_state()
    if not st.session_state["logged_in"]:
        login()
    else:
        home_dashboard()

if __name__ == "__main__":
    main()
