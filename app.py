import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import json
import base64
import io
import requests
import time

st.set_page_config(page_title="Sistem Koperasi Berjenjang", layout="centered")

# =========================================================================
# 🔐 GITHUB SECRETS
# =========================================================================
try:
    GITHUB_TOKEN = st.secrets["github"]["token"]
    REPO_NAME = st.secrets["github"]["repo"]
except Exception:
    GITHUB_TOKEN = ""
    REPO_NAME = ""

DB_FILE = "data_store.json"

# Template awal daftar user/akun login
TEMPLATE_AWAL = {
    "database": [],
    "users": [
        {"username": "karu_lt1", "role": "Karu", "password": "123", "status_akun": "Aktif", "password_baru": ""},
        {"username": "karu_lt2", "role": "Karu", "password": "123", "status_akun": "Aktif", "password_baru": ""},
        {"username": "kabid_pusat", "role": "Kabid", "password": "123", "status_akun": "Aktif", "password_baru": ""},
        {"username": "dir_utama", "role": "Direktur", "password": "123", "status_akun": "Aktif", "password_baru": ""},
        {"username": "admin_sdm", "role": "SDM", "password": "123", "status_akun": "Aktif", "password_baru": ""}
    ]
}

def canvas_to_base64(canvas_data):
    if canvas_data is not None:
        try:
            img = Image.fromarray(canvas_data.astype('uint8'), 'RGBA')
            if img.getbbox() is not None:
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                return base64.b64encode(buffered.getvalue()).decode()
        except Exception:
            pass
    return None

def load_data_from_github():
    if GITHUB_TOKEN.startswith("ghp_") and "/" in REPO_NAME:
        url = f"https://api.github.com/repos/{REPO_NAME}/contents/{DB_FILE}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            file_content = response.json()
            content_decoded = base64.b64decode(file_content["content"]).decode("utf-8")
            if content_decoded.strip() == "":
                return TEMPLATE_AWAL, file_content.get("sha", None)
            try:
                data = json.loads(content_decoded)
                if "database" not in data: data["database"] = []
                if "users" not in data: data["users"] = TEMPLATE_AWAL["users"]
                return data, file_content["sha"]
            except Exception:
                return TEMPLATE_AWAL, file_content.get("sha", None)
    return TEMPLATE_AWAL, None

def push_database_to_github(updated_data, sha_lama, message):
    json_string = json.dumps(updated_data, indent=4, ensure_ascii=False)
    content_encoded = base64.b64encode(json_string.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{DB_FILE}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}", 
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    payload = {"message": message, "content": content_encoded}
    if sha_lama:
        payload["sha"] = sha_lama
    res = requests.put(url, headers=headers, json=payload)
    return res.status_code in [200, 201]

data_saat_ini, sha_saat_ini = load_data_from_github()

# =========================================================================
# 🔑 LOGIN & RESET PASSWORD SYSTEM
# =========================================================================
st.sidebar.title("🏛️ Akses Sistem")
menu_login = st.sidebar.radio("Menu Akses", ["Masuk Aplikasi", "Lupa / Reset Password"])

user_login_aktif = None
role_aktif = "User Biasa"

if "preview_data" not in st.session_state:
    st.session_state.preview_data = None

if menu_login == "Masuk Aplikasi":
    role_pilihan = st.sidebar.selectbox("Pilih Opsi Login", ["User", "Karu (Kepala Regu)", "Kabid", "Direktur", "SDM", "Admin"])
    
    if role_pilihan == "User":
        role_aktif = "User Biasa"
    
    elif role_pilihan in ["Karu (Kepala Regu)", "Kabid", "Direktur", "SDM", "Admin"]:
        # Filter role spesifik yang dipilih pada dropdown sidebar
        role_mapping = {
            "Karu (Kepala Regu)": "Karu",
            "Kabid": "Kabid",
            "Direktur": "Direktur",
            "SDM": "SDM",
            "Admin": "Admin"
        }
        target_role = role_mapping[role_pilihan]
        
        user_list = [u["username"] for u in data_saat_ini["users"] if u["role"] == target_role]
        
        if not user_list:
            st.sidebar.warning(f"Belum ada akun dengan role {target_role} terdaftar. Silakan buat via akun SDM terlebih dahulu.")
        else:
            username_pilih = st.sidebar.selectbox("Pilih Username", user_list)
            password_input = st.sidebar.text_input("Password", type="password")
            
            if st.sidebar.button("Log In"):
                cocok = False
                for u in data_saat_ini["users"]:
                    if u["username"] == username_pilih:
                        if u["status_akun"] == "Menunggu Reset":
                            st.sidebar.error("⚠️ Akun ini terkunci! Menunggu reset oleh SDM.")
                            cocok = True
                            break
                        elif u["password"] == password_input:
                            st.session_state.user_login_aktif = u
                            st.sidebar.success(f"Berhasil Login: {u['username']} ({u['role']})")
                            cocok = True
                            st.rerun()
                if not cocok and password_input:
                    st.sidebar.error("❌ Password salah.")
                    
        if "user_login_aktif" in st.session_state:
            user_login_aktif = st.session_state.user_login_aktif
            role_aktif = user_login_aktif["role"]
            st.sidebar.info(f"🔑 Role Aktif: **{role_aktif}** | User: **{user_login_aktif['username']}**")
            if st.sidebar.button("🚪 Keluar (Logout)"):
                del st.session_state.user_login_aktif
                st.rerun()

elif menu_login == "Lupa / Reset Password":
    st.subheader("🔑 Formulir Pengajuan Reset Password")
    st.write("Lupa password akses akun? Pilih username Anda dan buat password baru. Perubahan ini akan aktif setelah disetujui tim SDM.")
    
    with st.form("form_reset_pass"):
        u_reset = st.selectbox("Pilih Username Anda", [u["username"] for u in data_saat_ini["users"]])
        p_baru1 = st.text_input("Password Baru", type="password")
        p_baru2 = st.text_input("Ulangi Password Baru", type="password")
        
        if st.form_submit_button("Ajukan Reset Password"):
            if not p_baru1 or not p_baru2:
                st.error("❌ Password baru tidak boleh kosong!")
            elif p_baru1 != p_baru2:
                st.error("❌ Konfirmasi password baru tidak cocok!")
            else:
                for u in data_saat_ini["users"]:
                    if u["username"] == u_reset:
                        u["status_akun"] = "Menunggu Reset"
                        u["password_baru"] = p_baru1
                        break
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"Reset User: {u_reset}"):
                    st.success("✅ Berhasil diajukan! Harap lapor ke tim SDM untuk membuka gembok akun.")

# =========================================================================
# 🏛️ HALAMAN UTAMA CORE PORTAL KOPERASI
# =========================================================================
st.title("🏛️ Portal Otomasi Koperasi Berjenjang")
st.write(f"**Status Akses Saat Ini:** *{role_aktif}*")
st.write("---")

# ---------------------------------------------------------------------
# 📝 USER BIASA (FORMULIR PENGAJUAN)
# ---------------------------------------------------------------------
if role_aktif == "User Biasa":
    st.subheader("📝 Formulir Pengajuan Berkas Pinjaman")
    with st.form("form_pengajuan"):
        nama = st.text_input("Nama Lengkap Anggota Pemohon")
        no_anggota = st.text_input("No Anggota")
        
        c_lok1, c_lok2 = st.columns(2)
        with c_lok1:
            lantai_asal = st.selectbox("Pilih Lantai Asal Pengaju", ["Lantai 1", "Lantai 2", "Lantai 3", "Lantai 4", "Lantai 5", "Lantai 6"])
        with c_lok2:
            unit = st.selectbox("Asal Unit / Bagian", ["IT", "Back Office", "HRD", "Keuangan", "Produksi", "Umum"])
            
        st.markdown("---")
        st.write("<b>👤 Pilih Supervisor / Karu (Kepala Regu) Tujuan:</b>", unsafe_allow_html=True)
        
        # Ambil daftar username yang ber-role 'Karu' saja untuk di-input pemohon
        karu_list = [u["username"] for u in data_saat_ini["users"] if u["role"] == "Karu"]
        if not karu_list:
            st.error("❌ Belum ada akun Karu (Kepala Regu) yang terdaftar di sistem! Harap hubungi SDM.")
            target_karu = ""
        else:
            target_karu = st.selectbox("Target Username Karu", karu_list)

        st.markdown("---")
        nominal = st.number_input("Nominal Pinjaman (Rp)", min_value=0, step=50000)
        keperluan = st.text_area("Keperluan / Alasan")
        
        col_ttd1, col_ttd2 = st.columns(2)
        with col_ttd1:
            st.write("✒️ **Tanda Tangan Pemohon:**")
            cv_user = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=110, width=220, key="cv_user")
        with col_ttd2:
            st.write("✒️ **Tanda Tangan Istri / Keluarga (Penjamin):**")
            cv_keluarga = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=110, width=220, key="cv_keluarga")
            st.caption("*(Harap cantumkan nama jelas penjamin di bawah ini)*")
            nama_istri_saudara = st.text_input("Nama Jelas Istri / Saudara", placeholder="Nama lengkap penjamin...")
        
        cek_review = st.form_submit_button("🔍 Tinjau & Cek Data")
        if cek_review:
            ttd_user = canvas_to_base64(cv_user.image_data)
            ttd_keluarga = canvas_to_base64(cv_keluarga.image_data)
            
            if not nama.strip() or not no_anggota.strip():
                st.error("❌ Nama dan Nomor Anggota wajib diisi!")
            elif not target_karu:
                st.error("❌ Target Karu (Kepala Regu) belum ditentukan!")
            elif not nama_istri_saudara.strip():
                st.error("❌ Nama Jelas Istri / Saudara wajib diisi!")
            elif not ttd_user or not ttd_keluarga:
                st.error("❌ Tanda tangan Pemohon & Keluarga wajib dilengkapi!")
            else:
                st.session_state.preview_data = {
                    "nama": nama.strip(), "no_anggota": no_anggota.strip(), 
                    "lantai_asal": lantai_asal, "unit": unit,
                    "target_karu": target_karu, # Tersimpan spesifik username karu tujuan
                    "nama_istri_saudara": nama_istri_saudara.strip(),
                    "nominal": nominal, "keperluan": keperluan.strip(),
                    "ttd_pengaju": ttd_user, "ttd_keluarga": ttd_keluarga,
                    "status": "Menunggu Verifikasi Karu", 
                    "ttd_kadiv": "", "ttd_kabid": "", "ttd_direktur": ""
                }

    if st.session_state.preview_data is not None:
        p = st.session_state.preview_data
        st.warning("⚠️ **Konfirmasi Pratinjau Berkas Sebelum Dikirim**")
        st.info(f"**Pemohon:** {p['nama']} ({p['lantai_asal']} - {p['unit']})\n\n**Tujuan Karu:** *{p['target_karu']}* | **Penjamin:** *{p['nama_istri_saudara']}* \n\n**Nominal:** Rp {p['nominal']:,}")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✏️ Edit Kembali Data"):
                st.session_state.preview_data = None
                st.rerun()
        with c2:
            if st.button("🚀 Data Sudah Yakin, Kirim Berkas!"):
                data_saat_ini["database"].append(p)
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"Baru: {p['nama']}"):
                    st.success(f"✅ Sukses! Pengajuan terkirim ke Karu: {p['target_karu']}.")
                    st.session_state.preview_data = None
                    time.sleep(1.2); st.rerun()

# ---------------------------------------------------------------------
# ✅ KARU (KEPALA REGU) - HANYA MEMPROSES BERKAS YANG DITUJUKAN KE USERNAME-NYA
# ---------------------------------------------------------------------
elif role_aktif == "Karu":
    st.subheader(f"👋 Selamat Datang Kepala Regu (Karu): {user_login_aktif['username']}")
    st.info("Anda berwenang meng-ACC berkas pengajuan yang ditujukan langsung ke akun Anda.")
    
    # Filter ketat: hanya munculkan data jika status Menunggu Karu DAN target_karu sama dengan username login
    items = [
        i for i in data_saat_ini["database"] 
        if i.get("status") == "Menunggu Verifikasi Karu" and i.get("target_karu") == user_login_aktif["username"]
    ]
    
    if not items: 
        st.info("Bersih! Belum ada antrean berkas pinjaman yang masuk ke akun Anda.")
        
    for idx, item in enumerate(items):
        st.markdown("### 📋 Berkas Pengajuan Masuk")
        st.success(f"Diajukan Kepada Anda (Karu Tujuan): **{item.get('target_karu')}**")
        
        st.write(f"**Nama Pemohon:** {item['nama']} ({item.get('lantai_asal')} - {item.get('unit')})")
        st.write(f"**Penjamin (Istri/Saudara):** **{item.get('nama_istri_saudara', '-')}**")
        st.write(f"**Nominal:** Rp {item['nominal']:,} | **Keperluan:** {item['keperluan']}")
        
        c_img1, c_img2 = st.columns(2)
        with c_img1:
            st.caption("Tanda Tangan Pemohon:")
            st.image(base64.b64decode(item["ttd_pengaju"]), width=120)
        with c_img2:
            st.caption(f"Tanda Tangan Penjamin ({item.get('nama_istri_saudara', 'Istri/Saudara')}):")
            st.image(base64.b64decode(item["ttd_keluarga"]), width=120)
            
        st.write(f"**Tanda Tangan ACC Karu ({user_login_aktif['username']}):**")
        cv_div = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=110, width=220, key=f"cv_karu_{idx}")
        
        if st.button("✍️ Setujui & Teruskan Berkas", key=f"btn_karu_{idx}"):
            ttd_div = canvas_to_base64(cv_div.image_data)
            if not ttd_div:
                st.error("❌ Tanda tangan wajib diisi sebelum verifikasi!")
            else:
                for d in data_saat_ini["database"]:
                    if str(d["no_anggota"]).strip() == str(item["no_anggota"]).strip() and d.get("status") == "Menunggu Verifikasi Karu":
                        d["status"] = "Menunggu Bidang"
                        d["ttd_kadiv"] = ttd_div  # Tetap memakai key ttd_kadiv untuk alur cetak PDF
                        break
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"Karu ACC: {item['nama']}"):
                    st.success("✅ Berhasil disetujui Karu! Berkas dilanjutkan ke Kepala Bidang (Kabid).")
                    time.sleep(1.2); st.rerun()
        st.write("---")

# ---------------------------------------------------------------------
# ✅ KABID (KEPALA BIDANG)
# ---------------------------------------------------------------------
elif role_aktif == "Kabid":
    st.subheader("👋 Selamat Datang Kepala Bidang (Kabid)")
    items_kabid = [i for i in data_saat_ini["database"] if i.get("status") == "Menunggu Bidang"]
    
    if not items_kabid:
        st.info("Tidak ada berkas yang menunggu verifikasi Kabid saat ini.")
        
    for idx, item in enumerate(items_kabid):
        st.markdown(f"### Berkas: {item['nama']} — Status: **{item['status']}**")
        st.write(f"**Dari Karu Tujuan:** *{item.get('target_karu', '-')}* | **Rp {item['nominal']:,}**")
        
        st.write(f"**Tanda Tangan ACC Kepala Bidang (Kabid):**")
        cv_kabid = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=110, width=220, key=f"cv_kabid_{idx}")
        
        if st.button("✍️ ACC & Teruskan ke Direktur", key=f"btn_kabid_{idx}"):
            ttd_kabid = canvas_to_base64(cv_kabid.image_data)
            if not ttd_kabid:
                st.error("❌ Tanda tangan wajib diisi sebelum verifikasi!")
            else:
                for d in data_saat_ini["database"]:
                    if str(d["no_anggota"]).strip() == str(item["no_anggota"]).strip() and d.get("status") == "Menunggu Bidang":
                        d["status"] = "Menunggu Direktur"
                        d["ttd_kabid"] = ttd_kabid
                        break
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"Kabid ACC: {item['nama']}"):
                    st.success("✅ Berhasil disetujui Kabid! Diteruskan ke Direktur."); time.sleep(1.2); st.rerun()
        st.write("---")

# ---------------------------------------------------------------------
# ✅ DIREKTUR
# ---------------------------------------------------------------------
elif role_aktif == "Direktur":
    st.subheader("👋 Selamat Datang Direktur Utama")
    items_dir = [i for i in data_saat_ini["database"] if i.get("status") == "Menunggu Direktur"]
    
    if not items_dir:
        st.info("Tidak ada berkas yang menunggu ACC Direktur saat ini.")
        
    for idx, item in enumerate(items_dir):
        st.markdown(f"### Berkas: {item['nama']} — Status: **{item['status']}**")
        st.write(f"**Dari Karu:** *{item.get('target_karu', '-')}* | **Rp {item['nominal']:,}**")
        
        st.write(f"**Tanda Tangan ACC Direktur Utama:**")
        cv_dir = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=110, width=220, key=f"cv_dir_{idx}")
        
        if st.button("✍️ ACC / Setujui Final Berkas", key=f"btn_dir_{idx}"):
            ttd_dir = canvas_to_base64(cv_dir.image_data)
            if not ttd_dir:
                st.error("❌ Tanda tangan wajib diisi sebelum verifikasi!")
            else:
                for d in data_saat_ini["database"]:
                    if str(d["no_anggota"]).strip() == str(item["no_anggota"]).strip() and d.get("status") == "Menunggu Direktur":
                        d["status"] = "SELESAI"
                        d["ttd_direktur"] = ttd_dir
                        break
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"Direktur ACC: {item['nama']}"):
                    st.success("✅ Pengajuan telah di-ACC Direktur dan SELESAI."); time.sleep(1.2); st.rerun()
        st.write("---")

# ---------------------------------------------------------------------
# ✅ SDM & ADMIN (ADMIN PUSAT & MANAJEMEN AKUN LOGIN)
# ---------------------------------------------------------------------
elif role_aktif in ["SDM", "Admin"]:
    tab1, tab2, tab3 = st.tabs(["📋 Semua Berkas", "🔐 Reset Password Akses", "👥 Manajemen Akun Login"])
    
    # TAB 1: DAFTAR SELURUH BERKAS & CETAK PDF
    with tab1:
        st.subheader("🖨️ Arsip Berkas & Cetak PDF Resmi")
        
        # Tombol bypass darurat jika admin pusat ingin memaksa SELESAI
        st.write("---")
        st.subheader("🔓 Berkas Dalam Antrean Berjenjang")
        items_all = [i for i in data_saat_ini["database"] if i.get("status") != "SELESAI"]
        if not items_all: st.info("Semua berkas pengajuan sudah berstatus SELESAI.")
        
        for idx, it in enumerate(items_all):
            st.write(f"• **{it['nama']}** — Karu Tujuan: *{it.get('target_karu')}* — Status: *{it['status']}*")
            if st.button(f"Selesaikan Paksa ({it['nama']})", key=f"force_done_{idx}"):
                for d in data_saat_ini["database"]:
                    if str(d["no_anggota"]).strip() == str(it["no_anggota"]).strip() and d.get("status") == it["status"]:
                        d["status"] = "SELESAI"
                        break
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"Bypass SDM: {it['nama']}"):
                    st.success("Berkas dipaksa SELESAI."); time.sleep(1.2); st.rerun()
            st.write("---")

        st.write("---")
        st.subheader("📜 Daftar Berkas Selesai (Siap Cetak)")
        selesais = [i for i in data_saat_ini["database"] if i.get("status") == "SELESAI"]
        if "print_id" not in st.session_state: st.session_state.print_id = None
        
        for idx, s in enumerate(selesais):
            col1, col2 = st.columns([4, 2])
            with col1: 
                st.write(f"✅ **{s['nama']}** — Karu: {s.get('target_karu', '-')} — Rp {s['nominal']:,}")
            with col2:
                if st.button("🖨️ Buka Printer PDF", key=f"print_btn_{idx}"): st.session_state.print_id = s['no_anggota']
            
            if st.session_state.print_id == s['no_anggota']:
                if st.button("❌ Tutup Jendela Cetak", key=f"close_btn_{idx}"):
                    st.session_state.print_id = None
                    st.rerun()
                html_template = f"""
                <div id="print-area" style="padding:20px; border:2px solid #333; font-family:Arial; background:white; color:black; max-width:650px; margin:auto;">
                    <div style="text-align:center; border-bottom:3px double #333; padding-bottom:5px; margin-bottom:15px;">
                        <h3 style="margin:0;">FORMULIR PINJAMAN KOPERASI BERJENJANG</h3>
                    </div>
                    <table style="width:100%; font-size:13px; margin-bottom:20px;">
                        <tr><td><b>Nama Pemohon</b></td><td>: {s['nama']} (Lantai: {s.get('lantai_asal')} - Unit: {s.get('unit')})</td></tr>
                        <tr><td><b>No Anggota</b></td><td>: {s['no_anggota']}</td></tr>
                        <tr><td><b>Nominal Dana</b></td><td>: <b>Rp {s['nominal']:,}</b></td></tr>
                        <tr><td><b>Keperluan</b></td><td>: {s['keperluan']}</td></tr>
                        <tr><td><b>Karu Tujuan (ACC)</b></td><td>: {s.get('target_karu', '-')}</td></tr>
                        <tr><td><b>Penjamin (Istri/Saudara)</b></td><td>: {s.get('nama_istri_saudara', '-')}</td></tr>
                    </table>
                    <div style="display:table; width:100%; text-align:center; font-size:11px;">
                        <div style="display:table-row;">
                            <div style="display:table-cell; width:50%; padding-bottom:10px;">
                                <p style="margin:0 0 5px 0; font-weight:bold;">1. Pemohon (Anggota)</p>
                                <img src="data:image/png;base64,{s.get('ttd_pengaju','')}" style="height:50px; border:1px dashed #ccc;"/>
                            </div>
                            <div style="display:table-cell; width:50%; padding-bottom:10px;">
                                <p style="margin:0 0 5px 0; font-weight:bold;">2. Penjamin: {s.get('nama_istri_saudara','')}</p>
                                <img src="data:image/png;base64,{s.get('ttd_keluarga','')}" style="height:50px; border:1px dashed #ccc;"/>
                            </div>
                        </div>
                        <div style="display:table-row;">
                            <div style="display:table-cell; width:50%; padding-bottom:10px;">
                                <p style="margin:0 0 5px 0; font-weight:bold;">3. Karu (Kepala Regu)</p>
                                <img src="data:image/png;base64,{s.get('ttd_kadiv','')}" style="height:50px; border:1px dashed #ccc;"/>
                            </div>
                            <div style="display:table-cell; width:50%; padding-bottom:10px;">
                                <p style="margin:0 0 5px 0; font-weight:bold;">4. Kepala Bidang (Kabid)</p>
                                <img src="data:image/png;base64,{s.get('ttd_kabid','')}" style="height:50px; border:1px dashed #ccc;"/>
                            </div>
                        </div>
                        <div style="display:table-row;">
                            <div style="display:table-cell; width:50%;"></div>
                            <div style="display:table-cell; width:50%;">
                                <p style="margin:0 0 5px 0; font-weight:bold;">5. Direktur Koperasi</p>
                                <img src="data:image/png;base64,{s.get('ttd_direktur','')}" style="height:50px; border:1px dashed #ccc;"/>
                            </div>
                        </div>
                    </div>
                </div>
                <script>setTimeout(function(){{ window.print(); }}, 800);</script>
                """
                st.components.v1.html(html_template, height=450, scrolling=True)

    # TAB 2: RESET PASSWORD AKUN
    with tab2:
        st.subheader("🔐 Permintaan Reset Password Akun")
        user_reset = [u for u in data_saat_ini["users"] if u.get("status_akun") == "Menunggu Reset"]
        if not user_reset: st.info("Aman! Tidak ada permintaan reset password.")
        for u_item in user_reset:
            st.warning(f"⚠️ **Username:** *{u_item['username']}* (Role: {u_item['role']})")
            c_res1, c_res2 = st.columns(2)
            with c_res1:
                if st.button(f"✅ Setujui Password Baru ({u_item['username']})"):
                    u_item["password"] = u_item["password_baru"]
                    u_item["password_baru"] = ""
                    u_item["status_akun"] = "Aktif"
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Appr Reset: {u_item['username']}"):
                        st.success("Password akses baru diaktifkan!"); time.sleep(1.2); st.rerun()
            with c_res2:
                if st.button(f"❌ Tolak Reset ({u_item['username']})"):
                    u_item["password_baru"] = ""
                    u_item["status_akun"] = "Aktif"
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Rej Reset: {u_item['username']}"):
                        st.error("Reset dibatalkan."); time.sleep(1.2); st.rerun()

    # TAB 3: MANAJEMEN AKUN LOGIN (TAMBAH/HAPUS USER, KARU, KABID, DIREKTUR, SDM)
    with tab3:
        st.subheader("👥 Manajemen Akun Akses Sistem Berjenjang")
        
        # --- Form Tambah Akun Login ---
        with st.form("form_tambah_user"):
            st.write("<b>➕ Tambahkan Akun / Role Baru</b>", unsafe_allow_html=True)
            new_username = st.text_input("Username Baru (Tanpa spasi, Contoh: karu_lt6 atau kabid_cabang)")
            new_role = st.selectbox("Pilih Role / Hak Akses", ["Karu", "Kabid", "Direktur", "SDM", "Admin"])
            new_pass = st.text_input("Password Default", value="123")
            
            if st.form_submit_button("Tambahkan Akun"):
                if not new_username.strip():
                    st.error("Username wajib diisi!")
                else:
                    sudah_ada = False
                    for u in data_saat_ini["users"]:
                        if u["username"].lower() == new_username.strip().lower():
                            sudah_ada = True
                            break
                    
                    if sudah_ada:
                        st.error("Username tersebut sudah terdaftar!")
                    else:
                        data_saat_ini["users"].append({
                            "username": new_username.strip(),
                            "role": new_role,
                            "password": new_pass.strip(),
                            "status_akun": "Aktif",
                            "password_baru": ""
                        })
                        if push_database_to_github(data_saat_ini, sha_saat_ini, f"Tambah User: {new_username}"):
                            st.success(f"Akun {new_username} dengan role {new_role} berhasil ditambahkan!"); time.sleep(1.2); st.rerun()

        st.write("---")
        
        # --- Daftar Hapus Akun Login ---
        st.write("<b>🗑️ Hapus / Kurangi Akun Akses</b>", unsafe_allow_html=True)
        for u_item in data_saat_ini["users"]:
            col_u1, col_u2 = st.columns([4, 1])
            with col_u1:
                st.write(f"• **{u_item['username']}** — (Role: *{u_item['role']}* | Pass: `{u_item['password']}`)")
            with col_u2:
                if st.button(f"Hapus", key=f"del_user_{u_item['username']}"):
                    data_saat_ini["users"] = [u for u in data_saat_ini["users"] if u["username"] != u_item["username"]]
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Hapus User: {u_item['username']}"):
                        st.toast(f"Akun {u_item['username']} telah dihapus")
                        time.sleep(1.2); st.rerun()
