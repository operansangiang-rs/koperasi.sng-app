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

# Template awal daftar lantai/bagian yang bisa login
TEMPLATE_AWAL = {
    "database": [],
    "daftar_lantai": [
        {"nama_lantai": "Lantai 1", "password": "123", "status_akun": "Aktif", "password_baru": ""},
        {"nama_lantai": "Lantai 2", "password": "123", "status_akun": "Aktif", "password_baru": ""},
        {"nama_lantai": "Lantai 3", "password": "123", "status_akun": "Aktif", "password_baru": ""},
        {"nama_lantai": "Lantai 4", "password": "123", "status_akun": "Aktif", "password_baru": ""},
        {"nama_lantai": "Lantai 5", "password": "123", "status_akun": "Aktif", "password_baru": ""}
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
                if "daftar_lantai" not in data: data["daftar_lantai"] = TEMPLATE_AWAL["daftar_lantai"]
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

lantai_aktif = None
role_aktif = "User Biasa"

if "preview_data" not in st.session_state:
    st.session_state.preview_data = None

if menu_login == "Masuk Aplikasi":
    role_pilihan = st.sidebar.selectbox("Pilih Opsi Login", ["User Biasa (Pengaju)", "Kepala Divisi (Lantai)", "SDM (Admin Pusat)"])
    
    if role_pilihan == "User Biasa (Pengaju)":
        role_aktif = "User Biasa"
    
    elif role_pilihan == "Kepala Divisi (Lantai)":
        lantai_pilih = st.sidebar.selectbox("Pilih Lantai Anda", [l["nama_lantai"] for l in data_saat_ini["daftar_lantai"]])
        password_input = st.sidebar.text_input("Password", type="password")
        
        if st.sidebar.button("Log In Kepala Divisi"):
            cocok = False
            for l in data_saat_ini["daftar_lantai"]:
                if l["nama_lantai"] == lantai_pilih:
                    if l["status_akun"] == "Menunggu Reset":
                        st.sidebar.error("⚠️ Akun lantai ini terkunci! Menunggu persetujuan reset oleh SDM.")
                        cocok = True
                        break
                    elif l["password"] == password_input:
                        st.session_state.lantai_aktif = l["nama_lantai"]
                        st.sidebar.success(f"Berhasil Login: {l['nama_lantai']}")
                        cocok = True
                        st.rerun()
            if not cocok and password_input:
                st.sidebar.error("❌ Password salah.")
                
        if "lantai_aktif" in st.session_state:
            lantai_aktif = st.session_state.lantai_aktif
            role_aktif = "Kepala Divisi"
            st.sidebar.info(f"🔑 Area Otoritas: **{lantai_aktif}**")
            if st.sidebar.button("🚪 Keluar (Logout)"):
                del st.session_state.lantai_aktif
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
    st.write("Lupa password akses lantai? Pilih lantai Anda dan buat password baru. Perubahan ini akan aktif setelah disetujui tim SDM.")
    
    with st.form("form_reset_pass"):
        l_reset = st.selectbox("Pilih Lantai Anda", [l["nama_lantai"] for l in data_saat_ini["daftar_lantai"]])
        p_baru1 = st.text_input("Password Baru", type="password")
        p_baru2 = st.text_input("Ulangi Password Baru", type="password")
        
        if st.form_submit_button("Ajukan Reset Password"):
            if not p_baru1 or not p_baru2:
                st.error("❌ Password baru tidak boleh kosong!")
            elif p_baru1 != p_baru2:
                st.error("❌ Konfirmasi password baru tidak cocok!")
            else:
                for l in data_saat_ini["daftar_lantai"]:
                    if l["nama_lantai"] == l_reset:
                        l["status_akun"] = "Menunggu Reset"
                        l["password_baru"] = p_baru1
                        break
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"Reset Lantai: {l_reset}"):
                    st.success("✅ Berhasil diajukan! Harap lapor ke tim SDM untuk membuka gembok login.")

# =========================================================================
# 🏛️ HALAMAN UTAMA CORE PORTAL KOPERASI
# =========================================================================
st.title("🏛️ Portal Otomasi Koperasi Berjenjang")
st.write(f"**Status Akses Saat Ini:** *{'User Pengaju (Anggota)' if role_aktif == 'User Biasa' else 'Pejabat ' + role_aktif}*")
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
            lantai_asal = st.selectbox("Pilih Lantai Asal Pengaju", [l["nama_lantai"] for l in data_saat_ini["daftar_lantai"]])
        with c_lok2:
            unit = st.selectbox("Asal Unit / Bagian", ["IT", "Back Office", "HRD", "Keuangan", "Produksi", "Umum"])
            
        st.markdown("---")
        st.write("<b>👤 Input Pejabat yang Menyetujui:</b>", unsafe_allow_html=True)
        nama_pejabat = st.text_input(f"Nama Kepala Divisi / Pejabat Terkait", placeholder="Masukkan nama pejabat yang bertugas di lantai tersebut...")

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
            elif not nama_pejabat.strip():
                st.error("❌ Nama Pejabat yang menyetujui wajib diisi!")
            elif not nama_istri_saudara.strip():
                st.error("❌ Nama Jelas Istri / Saudara wajib diisi!")
            elif not ttd_user or not ttd_keluarga:
                st.error("❌ Tanda tangan Pemohon & Keluarga wajib dilengkapi!")
            else:
                st.session_state.preview_data = {
                    "nama": nama.strip(), "no_anggota": no_anggota.strip(), 
                    "lantai_asal": lantai_asal, "unit": unit,
                    "nama_pejabat": nama_pejabat.strip(), 
                    "nama_istri_saudara": nama_istri_saudara.strip(),
                    "nominal": nominal, "keperluan": keperluan.strip(),
                    "ttd_pengaju": ttd_user, "ttd_keluarga": ttd_keluarga,
                    "status": "Menunggu Verifikasi Kepala Divisi", 
                    "ttd_kadiv": "", "ttd_kabid": "", "ttd_direktur": ""
                }

    if st.session_state.preview_data is not None:
        p = st.session_state.preview_data
        st.warning("⚠️ **Konfirmasi Pratinjau Berkas Sebelum Dikirim**")
        st.info(f"**Pemohon:** {p['nama']} ({p['lantai_asal']} - {p['unit']})\n\n**Penjamin:** *{p['nama_istri_saudara']}* \n\n**Verifikator:** {p['nama_pejabat']} | **Nominal:** Rp {p['nominal']:,}")
        
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
# ✅ KEPALA DIVISI (NAMA PEJABAT MUNCUL OTOMATIS BERDASARKAN INPUT PENGAJU)
# ---------------------------------------------------------------------
elif role_aktif == "Kepala Divisi":
    st.subheader(f"👋 Selamat Datang Pejabat Area: {lantai_aktif}")
    st.info("Anda berwenang meng-ACC berkas pengajuan yang masuk untuk lantai Anda.")
    
    # Filter ketat hanya memunculkan data pengajuan dari lantai yang login saat ini
    items = [
        i for i in data_saat_ini["database"] 
        if i.get("status") == "Menunggu Verifikasi Kepala Divisi" and i.get("lantai_asal") == lantai_aktif
    ]
    
    if not items: 
        st.info(f"Bersih! Belum ada antrean berkas pinjaman untuk area {lantai_aktif}.")
        
    for idx, item in enumerate(items):
        # Otomatis mencetak / menyematkan nama pejabat yang bertugas di atas kartu
        st.markdown("### 📋 Berkas Pengajuan Masuk")
        st.success(f"Berkas Ini Ditujukan Kepada Anda: **{item.get('nama_pejabat', '-')}** ({lantai_aktif})")
        
        st.write(f"**Nama Pemohon:** {item['nama']} | **Unit:** {item.get('unit')}")
        st.write(f"**Penjamin (Istri/Saudara):** **{item.get('nama_istri_saudara', '-')}**")
        st.write(f"**Nominal:** Rp {item['nominal']:,} | **Keperluan:** {item['keperluan']}")
        
        c_img1, c_img2 = st.columns(2)
        with c_img1:
            st.caption("Tanda Tangan Pemohon:")
            st.image(base64.b64decode(item["ttd_pengaju"]), width=120)
        with c_img2:
            st.caption(f"Tanda Tangan Penjamin ({item.get('nama_istri_saudara', 'Istri/Saudara')}):")
            st.image(base64.b64decode(item["ttd_keluarga"]), width=120)
            
        st.write(f"**Tanda Tangan ACC Kepala Divisi — {item.get('nama_pejabat', '-')} :**")
        cv_div = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=110, width=220, key=f"cv_div_{idx}")
        
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
# ✅ SDM (ADMIN PUSAT: ACC FINAL, CETAK PDF, & EDIT BAGIAN LOGIN)
# ---------------------------------------------------------------------
elif role_aktif == "SDM":
    tab1, tab2, tab3 = st.tabs(["📋 Berkas Selesai/ACC", "🔐 Reset Password Akses", "👥 Pengaturan Bagian Login (Lantai)"])
    
    # TAB 1: FINALISASI & CETAK PDF
    with tab1:
        st.subheader("🏛️ Antrean Berkas Menunggu Persetujuan Final")
        items_sdm = [i for i in data_saat_ini["database"] if i.get("status") not in ["Menunggu Verifikasi Kepala Divisi", "SELESAI"]]
        
        if not items_sdm:
            st.info("Tidak ada data berjenjang yang menunggu di-ACC.")
            
        for idx, item in enumerate(items_sdm):
            st.markdown(f"### Berkas: {item['nama']} — Status Saat Ini: **{item['status']}**")
            st.write(f"**Lantai/Unit:** {item.get('lantai_asal')} ({item.get('unit')}) | **Rp {item['nominal']:,}**")
            st.caption(f"Ditujukan ke Pejabat: *{item.get('nama_pejabat', '-')}*")
            
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
            with col1: 
                st.write(f"✅ **{s['nama']}** — {s.get('lantai_asal')} — Rp {s['nominal']:,}")
                st.caption(f"Verifikator: <b>{s.get('nama_pejabat', '-')}</b> | Penjamin: <b>{s.get('nama_istri_saudara', '-')}</b>", unsafe_allow_html=True)
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
                        <tr><td><b>Kepala Divisi (ACC)</b></td><td>: {s.get('nama_pejabat', '-')}</td></tr>
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

    # TAB 2: RESET PASSWORD AKSES LANTAI
    with tab2:
        st.subheader("🔐 Permintaan Reset Password Akses Lantai")
        lantai_reset = [l for l in data_saat_ini["daftar_lantai"] if l.get("status_akun") == "Menunggu Reset"]
        if not lantai_reset: st.info("Aman! Tidak ada permintaan reset password.")
        for l_item in lantai_reset:
            st.warning(f"⚠️ **Akses Area / Lantai:** *{l_item['nama_lantai']}*")
            c_res1, c_res2 = st.columns(2)
            with c_res1:
                if st.button(f"✅ Setujui Password Baru ({l_item['nama_lantai']})"):
                    l_item["password"] = l_item["password_baru"]
                    l_item["password_baru"] = ""
                    l_item["status_akun"] = "Aktif"
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Appr Reset: {l_item['nama_lantai']}"):
                        st.success("Password akses baru diaktifkan!"); time.sleep(1.2); st.rerun()
            with c_res2:
                if st.button(f"❌ Tolak Reset ({l_item['nama_lantai']})"):
                    l_item["password_baru"] = ""
                    l_item["status_akun"] = "Aktif"
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Rej Reset: {l_item['nama_lantai']}"):
                        st.error("Reset dibatalkan."); time.sleep(1.2); st.rerun()

    # TAB 3: TAMBAH / KURANGI AKSES LANTAI LANGSUNG DARI APLIKASI
    with tab3:
        st.subheader("👥 Pengaturan Area Login (Lantai / Bagian)")
        
        # --- Form Tambah Lantai ---
        with st.form("form_tambah_lantai"):
            st.write("<b>➕ Tambah Akses Lantai / Bagian Baru</b>", unsafe_allow_html=True)
            new_lantai = st.text_input("Nama Lantai / Unit Baru (Contoh: Lantai 6)")
            new_pass = st.text_input("Password Default", value="123")
            
            if st.form_submit_button("Tambahkan Akses Area"):
                if not new_lantai.strip():
                    st.error("Nama lantai atau bagian wajib diisi!")
                else:
                    sudah_ada = False
                    for l in data_saat_ini["daftar_lantai"]:
                        if l["nama_lantai"].lower() == new_lantai.strip().lower():
                            sudah_ada = True
                            break
                    
                    if sudah_ada:
                        st.error("Akses area / lantai tersebut sudah terdaftar!")
                    else:
                        data_saat_ini["daftar_lantai"].append({
                            "nama_lantai": new_lantai.strip(),
                            "password": new_pass.strip(),
                            "status_akun": "Aktif",
                            "password_baru": ""
                        })
                        if push_database_to_github(data_saat_ini, sha_saat_ini, f"Tambah Lantai: {new_lantai}"):
                            st.success(f"Akses {new_lantai} berhasil ditambahkan!"); time.sleep(1.2); st.rerun()

        st.write("---")
        
        # --- Daftar Hapus Lantai ---
        st.write("<b>🗑️ Hapus / Kurangi Akses Area Login</b>", unsafe_allow_html=True)
        for l_item in data_saat_ini["daftar_lantai"]:
            col_l1, col_l2 = st.columns([4, 1])
            with col_l1:
                st.write(f"• **{l_item['nama_lantai']}** (Password: `{l_item['password']}`)")
            with col_l2:
                if st.button(f"Hapus", key=f"del_lantai_{l_item['nama_lantai']}"):
                    data_saat_ini["daftar_lantai"] = [l for l in data_saat_ini["daftar_lantai"] if l["nama_lantai"] != l_item["nama_lantai"]]
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Hapus Lantai: {l_item['nama_lantai']}"):
                        st.toast(f"Akses {l_item['nama_lantai']} telah dihapus")
                        time.sleep(1.2); st.rerun()
