import streamlit as st

st.set_page_config(page_title="Kalkulator Muat Armada", page_icon="🚛", layout="wide")

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

def login():
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.markdown("<h2 style='text-align: center;'>🚛 Kalkulator Muat Armada</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            st.write("Silakan Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Masuk")

            if submit:
                users_config = st.secrets.get("users", {})
                user_found = False
                for key, val in users_config.items():
                    if key.endswith("_username") and val == username:
                        prefix = key.replace("_username", "")
                        pass_key = f"{prefix}_password"
                        if users_config.get(pass_key) == password:
                            user_found = True
                            st.session_state["logged_in"] = True
                            st.session_state["username"] = username
                            st.session_state["role"] = "admin" if prefix == "admin" else "sales"
                            st.rerun()
                            break
                if not user_found:
                    st.error("Username atau password salah")

def main():
    init_session_state()

    if not st.session_state["logged_in"]:
        login()
    else:
        st.write("## 🚛 Selamat Datang di Kalkulator Muat Armada")
        st.write("Silakan pilih menu di sidebar untuk mulai menggunakan aplikasi.")
        
        st.sidebar.title(f"Halo, {st.session_state['username']}!")
        st.sidebar.write(f"Role: {st.session_state['role'].capitalize()}")
        if st.sidebar.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()
