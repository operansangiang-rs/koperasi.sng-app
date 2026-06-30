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

# Template awal database disesuaikan dengan daftar pejabat per lantai & Master Password 123456 untuk SDM
TEMPLATE_AWAL = {
    "database": [],
    "users": [
        {"username": "lt1_ratih", "nama": "Ratih (Lt 1)", "role": "Kepala Divisi", "password": "123", "status_akun": "Aktif", "password_baru": ""},
        {"username": "lt2_fitri", "nama": "Fitri (Lt 2)", "role": "Kepala Divisi", "password": "123", "status_akun": "Aktif", "password_baru": ""},
        {"username": "lt3_aisyah", "nama": "Aisyah (Lt 3)", "role": "Kepala Divisi", "password": "123", "status_akun": "Aktif", "password_baru": ""},
        {"username": "lt4_hesti", "nama": "Hesti (Lt 4)", "role": "Kepala Divisi", "password": "123", "status_akun": "Aktif", "password_baru": ""},
        {"username": "lt5_nuni", "nama": "Nuni (Lt 5)", "role": "Kepala Divisi", "password": "123", "status_akun": "Aktif", "password_baru": ""}
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

user_aktif = None
role_aktif = "User Biasa"

if "preview_data" not in st.session_state:
    st.session_state.preview_data = None

if menu_login == "Masuk Aplikasi":
    role_pilihan = st.sidebar.selectbox("Pilih Opsi Login", ["User Biasa (Pengaju)", "Kepala Divisi (Lt 1 s/d 5)", "SDM (Admin Pusat)"])
    
    if role_pilihan == "User Biasa (Pengaju)":
        role_aktif = "User Biasa"
    
    elif role_pilihan == "Kepala Divisi (Lt 1 s/d 5)":
        username_input = st.sidebar.selectbox("Username Pejabat", [u["username"] for u in data_saat_ini["users"]])
        password_input = st.sidebar.text_input("Password", type="password")
        
        if st.sidebar.button("Log In Kepala Divisi"):
            cocok = False
            for u in data_saat_ini["users"]:
                if u["username"] == username_input:
                    if u["status_akun"] == "Menunggu Reset":
                        st.sidebar.error("⚠️ Akun Anda terkunci! Menunggu persetujuan reset oleh SDM.")
                        cocok = True
                        break
                    elif u["password"] == password_input:
                        st.session_state.user_aktif = u
                        st.sidebar.success(f"Selamat Datang, {u['nama']}")
                        cocok = True
                        st.rerun()
            if not cocok and password_input:
                st.sidebar.error("❌ Password salah.")
                
        if "user_aktif" in st.session_state:
            user_aktif = st.session_state.user_aktif
            role_aktif = "Kepala Divisi"
            st.sidebar.info(f"🔑 Logged in: {user_aktif['nama']}")
            if st.sidebar.button("🚪 Keluar (Logout)"):
                del st.session_state.user_aktif
                st.rerun()
                
    elif role_pilihan == "SDM (Admin Pusat)":
        pass_sdm = st.sidebar.text_input("Password Master SDM", type="password")
        if pass_sdm == "123456":
            role_aktif = "SDM"
            st.sidebar.success("Akses SDM Terbuka")
        elif pass_sdm:
            st.sidebar.error("Password Master Salah")

elif menu_login == "Lupa / Reset Password":
    st.subheader("🔑 Formulir Pengajuan Reset Password")
    st.write("Lupa password? Masukkan username Anda dan buat password baru. Perubahan ini akan aktif setelah disetujui tim SDM.")
    
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
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"Minta Reset: {u_reset}"):
                    st.success("✅ Berhasil diajukan! Harap lapor ke tim SDM untuk membuka gembok akun.")

# =========================================================================
# 🏛️ HALAMAN UTAMA CORE PORTAL KOPERASI
# =========================================================================
st.title("🏛️ Portal Otomasi Koperasi Berjenjang")
st.write(f"**Status Akses Saat Ini:** *{'User Pengaju (Anggota)' if role_aktif == 'User Biasa' else role_aktif}*")
st.write("---")

# ---------------------------------------------------------------------
# 📝 USER BIASA (FORMULIR PENGAJUAN)
# ---------------------------------------------------------------------
if role_aktif == "User Biasa":
    st.subheader("📝 Formulir Pengajuan Berkas Pinjaman")
    with st.form("form_pengajuan"):
        nama = st.text_input("Nama Lengkap")
        no_anggota = st.text_input("No Anggota")
        
        c_lok1, c_lok2 = st.columns(2)
        with c_lok1:
            lantai_asal = st.selectbox("Pilih Lantai Asal Pengaju", ["Lantai 1", "Lantai 2", "Lantai 3", "Lantai 4", "Lantai 5"])
        with c_lok2:
            unit = st.selectbox("Asal Unit / Bagian", ["IT", "Back Office", "HRD", "Keuangan", "Produksi", "Umum"])
            
        nominal = st.number_input("Nominal Pinjaman (Rp)", min_value=0, step=50000)
        keperluan = st.text_area("Keperluan / Alasan")
        
        col_ttd1, col_ttd2 = st.columns(2)
        with col_ttd1:
            st.write("✒️ **Tanda Tangan Pemohon:**")
            cv_user = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=120, width=240, key="cv_user")
        with col_ttd2:
            st.write("✒️ **Tanda Tangan Istri / Keluarga:**")
            cv_keluarga = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=120, width=240, key="cv_keluarga")
        
        cek_review = st.form_submit_button("🔍 Tinjau & Cek Data")
        if cek_review:
            ttd_user = canvas_to_base64(cv_user.image_data)
            ttd_keluarga = canvas_to_base64(cv_keluarga.image_data)
            
            if not nama.strip() or not no_anggota.strip():
                st.error("❌ Nama dan Nomor Anggota wajib diisi!")
            elif not ttd_user or not ttd_keluarga:
                st.error("❌ Tanda tangan Pemohon & Keluarga wajib dilengkapi!")
            else:
                st.session_state.preview_data = {
                    "nama": nama.strip(), "no_anggota": no_anggota.strip(), 
                    "lantai_asal": lantai_asal, "unit": unit,
                    "nominal": nominal, "keperluan": keperluan.strip(),
                    "ttd_pengaju": ttd_user, "ttd_keluarga": ttd_keluarga,
                    "status": "Menunggu Verifikasi Kepala Divisi", 
                    "ttd_kadiv": "", "ttd_kabid": "", "ttd_direktur": ""
                }

    if st.session_state.preview_data is not None:
        p = st.session_state.preview_data
        st.warning("⚠️ **Konfirmasi Pratinjau Berkas Sebelum Dikirim**")
        st.info(f"**Nama:** {p['nama']} ({p['lantai_asal']} - {p['unit']}) | **Nominal:** Rp {p['nominal']:,}")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✏️ Edit Kembali Data"):
                st.session_state.preview_data = None
                st.rerun()
        with c2:
            if st.button("🚀 Data Sudah Yakin, Kirim Berkas!"):
                data_saat_ini["database"].append(p)
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"Baru: {p['nama']}"):
                    st.success(f"✅ Sukses! Pengajuan terkirim ke Kepala Divisi {p['lantai_asal']}.")
                    st.session_state.preview_data = None
                    time.sleep(1.2); st.rerun()

# ---------------------------------------------------------------------
# ✅ KEPALA DIVISI (OTORISASI OTOMATIS BERDASARKAN USERNAME LOGIN)
# ---------------------------------------------------------------------
elif role_aktif == "Kepala Divisi":
    st.subheader(f"👋 Selamat Datang, Pejabat Divisi: {user_aktif['nama']}")
    
    # Menentukan lantai aktif berdasarkan username login yang dipilih
    # Misal login username "lt1_ratih" maka hanya memproses lantai "Lantai 1"
    mapping_lantai = {
        "lt1_ratih": "Lantai 1",
        "lt2_fitri": "Lantai 2",
        "lt3_aisyah": "Lantai 3",
        "lt4_hesti": "Lantai 4",
        "lt5_nuni": "Lantai 5"
    }
    lantai_otoritas = mapping_lantai.get(user_aktif["username"], "")
    
    st.info(f"Otoritas Area Kerja Anda: **{lantai_otoritas}**")
    
    # Filter ketat hanya memunculkan data pengajuan dari lantai yang bersangkutan
    items = [
        i for i in data_saat_ini["database"] 
        if i.get("status") == "Menunggu Verifikasi Kepala Divisi" and i.get("lantai_asal") == lantai_otoritas
    ]
    
    if not items: 
        st.info(f"Bersih! Belum ada antrean berkas pinjaman masuk untuk area {lantai_otoritas}.")
        
    for idx, item in enumerate(items):
        st.markdown(f"### 📋 Berkas: {item['nama']} — Unit: {item.get('unit')}")
        st.write(f"**Nominal Pinjaman:** Rp {item['nominal']:,} | **Keperluan:** {item['keperluan']}")
        
        c_img1, c_img2 = st.columns(2)
        with c_img1:
            st.caption("Tanda Tangan Pemohon:")
            st.image(base64.b64decode(item["ttd_pengaju"]), width=130)
        with c_img2:
            st.caption("Tanda Tangan Istri / Keluarga:")
            st.image(base64.b64decode(item["ttd_keluarga"]), width=130)
            
        st.write(f"**Tanda Tangan ACC Kepala Divisi {lantai_otoritas}:**")
        cv_div = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=120, width=240, key=f"cv_div_{idx}")
        
        if st.button("✍️ Setujui & Teruskan Berkas", key=f"btn_div_{idx}"):
            ttd_div = canvas_to_base64(cv_div.image_data)
            if not ttd_div:
                st.error("❌ Tanda tangan wajib diisi sebelum verifikasi!")
            else:
                for d in data_saat_ini["database"]:
                    if str(d["no_anggota"]).strip() == str(item["no_anggota"]).strip() and d.get("status") == "Menunggu Verifikasi Kepala Divisi":
                        d["status"] = "Menunggu Bidang"
                        d["ttd_kadiv"] = ttd_div
                        break
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"Kadiv ACC: {item['nama']}"):
                    st.success("✅ Berhasil disetujui Kadiv! Berkas dilanjutkan ke Kepala Bidang.")
                    time.sleep(1.2); st.rerun()
        st.write("---")

# ---------------------------------------------------------------------
# ✅ SDM (ADMIN PUSAT: ACC FINAL, CETAK PDF, & MANAJEMEN USER)
# ---------------------------------------------------------------------
elif role_aktif == "SDM":
    tab1, tab2, tab3 = st.tabs(["📋 Berkas Selesai/ACC", "🔐 Reset Password", "👥 Manajemen Role Login Pejabat"])
    
    # TAB 1: FINALISASI & CETAK PDF
    with tab1:
        st.subheader("🏛️ Antrean Berkas Menunggu Persetujuan Final")
        items_sdm = [i for i in data_saat_ini["database"] if i.get("status") not in ["Menunggu Verifikasi Kepala Divisi", "SELESAI"]]
        
        if not items_sdm:
            st.info("Tidak ada data berjenjang yang menunggu di-ACC.")
            
        for idx, item in enumerate(items_sdm):
            st.markdown(f"### Berkas: {item['nama']} — Status Saat Ini: **{item['status']}**")
            st.write(f"**Lantai/Unit:** {item.get('lantai_asal')} ({item.get('unit')}) | **Rp {item['nominal']:,}**")
            
            # Tombol percepat ACC langsung selesai (Simulasi pintasan Admin Pusat jika diperlukan)
            if st.button(f"🔒 Setujui / Nyatakan SELESAI ({item['nama']})", key=f"force_acc_{idx}"):
                for d in data_saat_ini["database"]:
                    if str(d["no_anggota"]).strip() == str(item["no_anggota"]).strip() and d.get("status") == item["status"]:
                        d["status"] = "SELESAI"
                        break
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"ACC Kilat SDM: {item['nama']}"):
                    st.success("Berkas dinyatakan SELESAI secara sistem."); time.sleep(1.2); st.rerun()
            st.write("---")
            
        st.write("---")
        st.subheader("🖨️ Arsip Berkas Cetak PDF Resmi")
        selesais = [i for i in data_saat_ini["database"] if i.get("status") == "SELESAI"]
        if "print_id" not in st.session_state: st.session_state.print_id = None
        
        for idx, s in enumerate(selesais):
            col1, col2 = st.columns([4, 2])
            with col1: st.write(f"✅ **{s['nama']}** — {s.get('lantai_asal')} — Rp {s['nominal']:,}")
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
                        <tr><td><b>Nama Pemohon</b></td><td>: {s['nama']} ({s.get('lantai_asal')} - {s.get('unit')})</td></tr>
                        <tr><td><b>No Anggota</b></td><td>: {s['no_anggota']}</td></tr>
                        <tr><td><b>Nominal Dana</b></td><td>: <b>Rp {s['nominal']:,}</b></td></tr>
                        <tr><td><b>Keperluan</b></td><td>: {s['keperluan']}</td></tr>
                    </table>
                    <div style="display:table; width:100%; text-align:center; font-size:11px;">
                        <div style="display:table-row;">
                            <div style="display:table-cell; width:50%; padding-bottom:10px;">
                                <p style="margin:0 0 5px 0; font-weight:bold;">1. Pemohon (Anggota)</p>
                                <img src="data:image/png;base64,{s.get('ttd_pengaju','')}" style="height:50px; border:1px dashed #ccc;"/>
                            </div>
                            <div style="display:table-cell; width:50%; padding-bottom:10px;">
                                <p style="margin:0 0 5px 0; font-weight:bold;">2. Penjamin Keluarga</p>
                                <img src="data:image/png;base64,{s.get('ttd_keluarga','')}" style="height:50px; border:1px dashed #ccc;"/>
                            </div>
                        </div>
                        <div style="display:table-row;">
                            <div style="display:table-cell; width:50%; padding-bottom:10px;">
                                <p style="margin:0 0 5px 0; font-weight:bold;">3. Kepala Divisi</p>
                                <img src="data:image/png;base64,{s.get('ttd_kadiv','')}" style="height:50px; border:1px dashed #ccc;"/>
                            </div>
                            <div style="display:table-cell; width:50%; padding-bottom:10px;">
                                <p style="margin:0 0 5px 0; font-weight:bold;">4. Kepala Bidang</p>
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

    # TAB 2: RESET PASSWORD
    with tab2:
        st.subheader("🔐 Permintaan Reset Password Pejabat")
        pejabat_reset = [u for u in data_saat_ini["users"] if u.get("status_akun") == "Menunggu Reset"]
        if not pejabat_reset: st.info("Aman! Tidak ada permintaan reset password.")
        for u_pej in pejabat_reset:
            st.warning(f"⚠️ **Username: {u_pej['username']}** — Nama: *{u_pej['nama']}*")
            c_res1, c_res2 = st.columns(2)
            with c_res1:
                if st.button(f"✅ Setujui Password Baru ({u_pej['username']})"):
                    u_pej["password"] = u_pej["password_baru"]
                    u_pej["password_baru"] = ""
                    u_pej["status_akun"] = "Aktif"
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Approved Reset: {u_pej['username']}"):
                        st.success("Password baru diaktifkan!"); time.sleep(1.2); st.rerun()
            with c_res2:
                if st.button(f"❌ Tolak Reset ({u_pej['username']})"):
                    u_pej["password_baru"] = ""
                    u_pej["status_akun"] = "Aktif"
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Tolak Reset: {u_pej['username']}"):
                        st.error("Reset dibatalkan."); time.sleep(1.2); st.rerun()

    # TAB 3: TAMBAH / KURANGI ROLE PEJABAT LANGSUNG DARI APLIKASI
    with tab3:
        st.subheader("👥 Manajemen Akun Pejabat (Tambah / Kurang Role)")
        
        # --- Form Tambah Akun ---
        with st.form("form_tambah_user"):
            st.write("<b>➕ Tambah Role Akun Baru</b>", unsafe_allow_html=True)
            new_username = st.text_input("Username Baru (Tanpa spasi, misal: lt6_rully)")
            new_nama = st.text_input("Nama Lengkap Pejabat")
            new_pass = st.text_input("Password Default", value="123")
            
            if st.form_submit_button("Tambah Role Pejabat"):
                if not new_username.strip() or not new_nama.strip():
                    st.error("Username dan Nama wajib diisi!")
                else:
                    sudah_ada = False
                    for u in data_saat_ini["users"]:
                        if u["username"] == new_username.strip():
                            sudah_ada = True
                            break
                    
                    if sudah_ada:
                        st.error("Username tersebut sudah terdaftar di sistem!")
                    else:
                        data_saat_ini["users"].append({
                            "username": new_username.strip(),
                            "nama": new_nama.strip(),
                            "role": "Kepala Divisi",
                            "password": new_pass.strip(),
                            "status_akun": "Aktif",
                            "password_baru": ""
                        })
                        if push_database_to_github(data_saat_ini, sha_saat_ini, f"Tambah User: {new_username}"):
                            st.success(f"Role {new_username} berhasil ditambahkan!"); time.sleep(1.2); st.rerun()

        st.write("---")
        
        # --- Daftar Hapus Akun ---
        st.write("<b>🗑️ Hapus / Kurangi Role Akun</b>", unsafe_allow_html=True)
        for u_item in data_saat_ini["users"]:
            col_u1, col_u2 = st.columns([4, 1])
            with col_u1:
                st.write(f"• **{u_item['username']}** — {u_item['nama']}")
            with col_u2:
                # Tombol Hapus dikunci sementara biar admin tidak salah klik
                if st.button(f"Hapus", key=f"del_user_{u_item['username']}"):
                    data_saat_ini["users"] = [u for u in data_saat_ini["users"] if u["username"] != u_item["username"]]
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Hapus User: {u_item['username']}"):
                        st.toast(f"Akun {u_item['username']} telah dihapus")
                        time.sleep(1.2); st.rerun()
