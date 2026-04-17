# 🚛 Kalkulator Muat Armada

Aplikasi web untuk tim sales guna menghitung kapasitas muat barang (3D Bin Packing) ke dalam armada pengiriman (truk) berdasarkan volume dan tonase secara real-time.

## Struktur Folder

Project ini terstruktur sebagai berikut:
- `app.py`: Entry point aplikasi.
- `config.py`: Variabel konfigurasi umum.
- `requirements.txt`: Dependensi Python.
- `pages/`: 
  - `1_Simulator.py`: Halaman utama kalkulator armada.
  - `2_Admin_Panel.py`: Halaman untuk mengelola master data.
- `utils/`: Modul utilitas untuk GitHub, Google Sheets, Packing Engine, dsb.
- `data/`: Sample data excel untuk pengembangan (dapat dipindah ke GitHub repository sungguhan untuk produksi).
- `.streamlit/secrets.toml`: Penyimpanan token/kredensial secara aman (tidak disertakan dalam version control aslinya/template).

## Persiapan Aplikasi (Setup)

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Kredensial di `.streamlit/secrets.toml`**
   Anda perlu mengatur kredensial untuk GitHub dan Google Sheets:
   ```toml
   [github]
   token = "ISI_DENGAN_GITHUB_PERSONAL_ACCESS_TOKEN"
   repo = "username_anda/nama_repo"
   branch = "main"

   [gsheets]
   spreadsheet_id = "ISI_DENGAN_ID_SPREADSHEET_LOG"
   credentials_json = '{"type": "service_account", "project_id": "..."}'

   [users]
   admin_username = "admin"
   admin_password = "admin123"
   sales1_username = "sales1"
   sales1_password = "sales123"
   ```
   *Catatan: Jika token GitHub diisi dengan `"YOUR_GITHUB_TOKEN"`, aplikasi akan berjalan dalam "Development Mode" (menyimpan/membaca file Excel langsung ke sistem file lokal `kalkulator_muat/data/`).*

3. **Cara Mendapatkan Kredensial**
   - **GitHub**: Buka [GitHub Settings > Developer Settings > Personal access tokens](https://github.com/settings/tokens) dan buat token klasik dengan akses ke `repo`.
   - **Google Sheets**: Buat Service Account dari Google Cloud Console, aktifkan *Google Sheets API* & *Google Drive API*, buat JSON key file, kemudian berikan akses editor di file Spreadsheet Anda ke email service account tersebut. Di dalam Google Sheet Anda, pastikan terdapat worksheet/tab bernama `report_log`.

4. **Menjalankan Aplikasi Secara Lokal**
   ```bash
   streamlit run app.py
   ```

## Deploy ke Streamlit Community Cloud

1. Push seluruh folder project (kecuali folder data rahasia jika ada) ke GitHub. Jangan simpan `secrets.toml`.
2. Buka [share.streamlit.io](https://share.streamlit.io).
3. Connect dengan repository GitHub Anda dan arahkan "Main file path" ke `app.py`.
4. Di bagian **Advanced Settings**, pada kolom **Secrets**, salin semua isi dari `.streamlit/secrets.toml` milik Anda.
5. Klik "Deploy!".
