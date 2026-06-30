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

# Template awal database jika file JSON di GitHub masih kosong atau baru dibuat
TEMPLATE_AWAL = {
    "database": [],
    "users": [
        # Akun bawaan (Default) untuk simulasi awal, bisa ditambah lewat aplikasi nanti
        {"username": "kadiv_it", "nama": "Ahmad S.Kom", "role": "Kepala Divisi", "unit": "IT", "lantai": "Lantai 3", "password": "123", "status_akun": "Aktif", "password_baru": ""},
        {"username": "kadiv_bo1", "nama": "Siti Aminah", "role": "Kepala Divisi", "unit": "Back Office", "lantai": "Lantai 1", "password": "123", "status_akun": "Aktif", "password_baru": ""}
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
menu_login = st.sidebar.radio("Menu", ["Masuk Aplikasi", "Lupa / Reset Password"])

user_aktif = None
role_aktif = "User Biasa"
unit_aktif = None
lantai_aktif = None

if "preview_data" not in st.session_state:
    st.session_state.preview_data = None

if menu_login == "Masuk Aplikasi":
    role_pilihan = st.sidebar.selectbox("Pilih Role Login", ["User Biasa", "Pejabat Divisi / Direktur", "SDM (Admin Pusat)"])
    
    if role_pilihan == "User Biasa":
        role_aktif = "User Biasa"
    
    elif role_pilihan == "Pejabat Divisi / Direktur":
        username_input = st.sidebar.text_input("Username Pejabat")
        password_input = st.sidebar.text_input("Password", type="password")
        
        if st.sidebar.button("Log In Pejabat"):
            cocok = False
            for u in data_saat_ini["users"]:
                if u["username"] == username_input.strip():
                    if u["status_akun"] == "Menunggu Reset":
                        st.sidebar.error("⚠️ Akun Anda sedang dikunci! Menunggu persetujuan reset oleh SDM.")
                        cocok = True
                        break
                    elif u["password"] == password_input:
                        st.session_state.user_aktif = u
                        st.sidebar.success(f"Selamat Datang, {u['nama']}")
                        cocok = True
                        st.rerun()
            if not cocok and username_input:
                st.sidebar.error("❌ Username atau Password salah / Akun belum terdaftar.")
                
        if "user_aktif" in st.session_state:
            user_aktif = st.session_state.user_aktif
            role_aktif = user_aktif["role"]
            unit_aktif = user_aktif["unit"]
            lantai_aktif = user_aktif["lantai"]
            st.sidebar.info(f"🔑 Logged in: {user_aktif['nama']} ({unit_aktif} - {lantai_aktif})")
            if st.sidebar.button("🚪 Keluar (Logout)"):
                del st.session_state.user_aktif
                st.rerun()
                
    elif role_pilihan == "SDM (Admin Pusat)":
        pass_sdm = st.sidebar.text_input("Password Akun SDM", type="password")
        if pass_sdm == "123456":
            role_aktif = "SDM"
            st.sidebar.success("Akses SDM Terbuka")
        elif pass_sdm:
            st.sidebar.error("Password Master SDM Salah")

# --- FITUR AJUKAN RESET PASSWORD (MANUSIAWI & AMAN) ---
elif menu_login == "Lupa / Reset Password":
    st.subheader("🔑 Formulir Pengajuan Reset Password Pejabat")
    st.write("Jika Anda lupa password, silakan masukkan username Anda dan buat password baru di bawah. Perubahan ini akan aktif setelah **disetujui oleh tim SDM**.")
    
    with st.form("form_reset_pass"):
        u_reset = st.text_input("Masukkan Username Anda yang Terdaftar")
        p_baru1 = st.text_input("Masukkan Password Baru", type="password")
        p_baru2 = st.text_input("Ulangi Password Baru", type="password")
        
        if st.form_submit_button("Ajukan Reset Password ke SDM"):
            if not u_reset.strip() or not p_baru1 or not p_baru2:
                st.error("❌ Semua kolom wajib diisi!")
            elif p_baru1 != p_baru2:
                st.error("❌ Konfirmasi password baru tidak cocok!")
            else:
                user_ditemukan = False
                for u in data_saat_ini["users"]:
                    if u["username"] == u_reset.strip():
                        u["status_akun"] = "Menunggu Reset"
                        u["password_baru"] = p_baru1  # Ditampung sementara
                        user_ditemukan = True
                        break
                
                if user_ditemukan:
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Minta Reset: {u_reset}"):
                        st.success("✅ Permintaan berhasil dikirim! Akun dikunci sementara. Silakan hubungi Tim SDM di Lantai Pusat untuk menyetujui password baru Anda.")
                else:
                    st.error("❌ Username tidak ditemukan di sistem!")

# =========================================================================
# 🏛️ HALAMAN UTAMA CORE PORTAL KOPERASI
# =========================================================================
st.title("🏛️ Portal Otomasi Koperasi Berjenjang")
st.write(f"**Akses Aktif Anda:** {role_aktif if role_aktif != 'User Biasa' else 'Formulir Pengaju (Anggota)'}")
st.write("---")

# ---------------------------------------------------------------------
# 📝 USER BIASA (FORMULIR DENGAN UNIT DAN LANTAI)
# ---------------------------------------------------------------------
if role_aktif == "User Biasa":
    st.subheader("📝 Pengajuan Berkas Pinjaman")
    with st.form("form_pengajuan"):
        nama = st.text_input("Nama Lengkap")
        no_anggota = st.text_input("No Anggota")
        
        # Penambahan Struktur Lokasi Kerja Penjaminan
        c_lok1, c_lok2 = st.columns(2)
        with c_lok1:
            unit = st.selectbox("Asal Unit / Bagian Kerja", ["IT", "Back Office", "HRD", "Keuangan", "Produksi", "Logistik", "Umum"])
        with c_lok2:
            lantai = st.selectbox("Lokasi Lantai Kerja", ["Lantai 1", "Lantai 2", "Lantai 3", "Lantai 4", "Lantai 5"])
            
        nominal = st.number_input("Nominal Pinjaman (Rp)", min_value=0, step=50000)
        keperluan = st.text_area("Keperluan / Alasan")
        
        col_ttd1, col_ttd2 = st.columns(2)
        with col_ttd1:
            st.write("✒️ **Tanda Tangan Pemohon:**")
            cv_user = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=130, width=260, key="cv_user")
        with col_ttd2:
            st.write("✒️ **Tanda Tangan Istri / Keluarga:**")
            cv_keluarga = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=130, width=260, key="cv_keluarga")
        
        cek_review = st.form_submit_button("🔍 Tinjau & Cek Data")
        if cek_review:
            ttd_user = canvas_to_base64(cv_user.image_data)
            ttd_keluarga = canvas_to_base64(cv_keluarga.image_data)
            
            if not nama.strip() or not no_anggota.strip():
                st.error("❌ Nama dan Nomor Anggota wajib diisi!")
            elif not ttd_user or not ttd_keluarga:
                st.error("❌ Kedua tanda tangan wajib diisi lengkap!")
            else:
                st.session_state.preview_data = {
                    "nama": nama.strip(), "no_anggota": no_anggota.strip(), 
                    "unit": unit, "lantai": lantai,
                    "nominal": nominal, "keperluan": keperluan.strip(),
                    "ttd_pengaju": ttd_user, "ttd_keluarga": ttd_keluarga,
                    "status": "Menunggu Divisi", "ttd_kadiv": "", "ttd_kabid": "", "ttd_direktur": ""
                }

    if st.session_state.preview_data is not None:
        p = st.session_state.preview_data
        st.warning("⚠️ **Konfirmasi Pratinjau Berkas Sebelum Dikirim**")
        st.info(f"**Nama:** {p['nama']} ({p['unit']} - {p['lantai']}) | **Nominal:** Rp {p['nominal']:,}")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✏️ Edit Kembali Data"):
                st.session_state.preview_data = None
                st.rerun()
        with c2:
            if st.button("🚀 Data Sudah Yakin, Kirim Berkas!"):
                data_saat_ini["database"].append(p)
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"Baru: {p['nama']}"):
                    st.success(f"✅ Sukses! Pengajuan terkirim otomatis ke Kepala Divisi {p['unit']} ({p['lantai']}).")
                    st.session_state.preview_data = None
                    time.sleep(1.5); st.rerun()

# ---------------------------------------------------------------------
# ✅ KEPALA DIVISI (ROLE ACCESS CONTROL BERDASARKAN UNIT & LANTAI)
# ---------------------------------------------------------------------
elif role_aktif == "Kepala Divisi":
    st.subheader(f"👋 Selamat Datang Kadiv: {user_aktif['nama']}")
    st.info(f"Otoritas Monitor Anda: **Unit {unit_aktif} — {lantai_aktif}**")
    
    # FILTER KETAT: Hanya menampilkan berkas yang sesuai Unit dan Lantai dari Kadiv yang sedang login
    items = [
        i for i in data_saat_ini["database"] 
        if i.get("status") == "Menunggu Divisi" and i.get("unit") == unit_aktif and i.get("lantai") == lantai_aktif
    ]
    
    if not items: 
        st.info(f"Bersih! Belum ada pengajuan baru dari anggota Unit {unit_aktif} {lantai_aktif}.")
        
    for idx, item in enumerate(items):
        st.markdown(f"### 📋 Berkas Pengajuan: {item['nama']}")
        st.write(f"**No Anggota:** {item['no_anggota']} | **Nominal Pinjaman:** Rp {item['nominal']:,}")
        st.write(f"**Keperluan:** {item['keperluan']}")
        
        c_img1, c_img2 = st.columns(2)
        with c_img1:
            st.caption("Tanda Tangan Pemohon:")
            st.image(base64.b64decode(item["ttd_pengaju"]), width=140)
        with c_img2:
            st.caption("Tanda Tangan Istri / Keluarga:")
            st.image(base64.b64decode(item["ttd_keluarga"]), width=140)
            
        st.write(f"**Silakan Berikan Tanda Tangan Persetujuan Kepala Divisi {unit_aktif}:**")
        cv_div = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=130, width=260, key=f"cv_div_{idx}")
        
        if st.button("✍️ Setujui & Teruskan Berkas", key=f"btn_div_{idx}"):
            ttd_div = canvas_to_base64(cv_div.image_data)
            if not ttd_div:
                st.error("❌ Anda wajib menandandatangani kanvas digital terlebih dahulu!")
            else:
                for d in data_saat_ini["database"]:
                    if str(d["no_anggota"]).strip() == str(item["no_anggota"]).strip() and d.get("status") == "Menunggu Divisi":
                        d["status"] = "Menunggu Bidang"
                        d["ttd_kadiv"] = ttd_div
                        break
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"Kadiv ACC: {item['nama']}"):
                    st.success("✅ Berhasil disetujui! Berkas dinaikkan ke level Kepala Bidang.")
                    time.sleep(1.2); st.rerun()
        st.write("---")

# ---------------------------------------------------------------------
# ✅ KEPALA BIDANG / DIREKTUR (LOGIKA AKSES SEPERTI SEBELUMNYA)
# ---------------------------------------------------------------------
elif role_aktif in ["Kepala Bidang", "Direktur"]:
    target_status = "Menunggu Bidang" if role_aktif == "Kepala Bidang" else "Menunggu Direktur"
    next_status = "Menunggu Direktur" if role_aktif == "Kepala Bidang" else "Menunggu SDM"
    ttd_key = "ttd_kabid" if role_aktif == "Kepala Bidang" else "ttd_direktur"
    
    items = [i for i in data_saat_ini["database"] if i.get("status") == target_status]
    if not items: 
        st.info(f"Tidak ada berkas yang menunggu verifikasi {role_aktif}.")
        
    for idx, item in enumerate(items):
        st.markdown(f"### 📋 Berkas: {item['nama']} (Unit: {item.get('unit')} - {item.get('lantai')})")
        st.write(f"**Nominal:** Rp {item['nominal']:,} | **Alasan:** {item['keperluan']}")
        
        st.write(f"**Tanda Tangan {role_aktif}:**")
        cv_pej = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=130, width=260, key=f"cv_pej_{idx}")
        
        if st.button(f"✍️ Setujui Sebagai {role_aktif}", key=f"btn_pej_{idx}"):
            ttd_pej = canvas_to_base64(cv_pej.image_data)
            if not ttd_pej:
                st.error("Tanda tangan wajib diisi!")
            else:
                for d in data_saat_ini["database"]:
                    if str(d["no_anggota"]).strip() == str(item["no_anggota"]).strip() and d.get("status") == target_status:
                        d["status"] = next_status
                        d[ttd_key] = ttd_pej
                        break
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"{role_aktif} ACC: {item['nama']}"):
                    st.success(f"✅ Disetujui oleh {role_aktif}!")
                    time.sleep(1.2); st.rerun()

# ---------------------------------------------------------------------
# ✅ SDM (ADMIN PUSAT: ACC FINAL & VERIFIKASI RESET PASSWORD)
# ---------------------------------------------------------------------
elif role_aktif == "SDM":
    tab1, tab2 = st.tabs(["📋 Antrean Kelayakan Pinjaman", "🔐 Persetujuan Reset Password Pejabat"])
    
    # TAB 1: FINAlISASI BERKAS PINJAMAN KOPERASI
    with tab1:
        if "print_id" not in st.session_state: st.session_state.print_id = None
        items = [i for i in data_saat_ini["database"] if i.get("status") == "Menunggu SDM"]
        if not items: st.info("Tidak ada berkas pinjaman masuk.")
        for idx, item in enumerate(items):
            st.markdown(f"### Final ACC: {item['nama']} — Unit {item.get('unit')} ({item.get('lantai')})")
            if st.button("🔒 NYATAKAN VALID & SELESAI", key=f"btn_sdm_{idx}"):
                for d in data_saat_ini["database"]:
                    if str(d["no_anggota"]).strip() == str(item["no_anggota"]).strip() and d.get("status") == "Menunggu SDM":
                        d["status"] = "SELESAI"
                        break
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"Final SDM: {item['nama']}"):
                    st.success("Berkas ditutup dengan status SELESAI!"); time.sleep(1.2); st.rerun()
                    
        # Bagian Cetak PDF Tetap Aman di Bawah
        st.write("---")
        st.subheader("🖨️ Arsip Berkas Cetak PDF Resmi")
        selesais = [i for i in data_saat_ini["database"] if i.get("status") == "SELESAI"]
        for idx, s in enumerate(selesais):
            col1, col2 = st.columns([4, 2])
            with col1: st.write(f"✅ **{s['nama']}** — Unit {s.get('unit')} — Rp {s['nominal']:,}")
            with col2:
                if st.button("🖨️ Buka Printer PDF", key=f"print_btn_{idx}"): st.session_state.print_id = s['no_anggota']
            
            if st.session_state.print_id == s['no_anggota']:
                if st.button("❌ Tutup Jendela Cetak", key=f"close_btn_{idx}"):
                    st.session_state.print_id = None
                    st.rerun()
                # Kode HTML Template Cetak multi ttd (Pemohon, Istri, Kadiv, Kabid, Direktur)
                html_template = f"""
                <div id="print-area" style="padding:20px; border:2px solid #333; font-family:Arial; background:white; color:black; max-width:650px; margin:auto;">
                    <div style="text-align:center; border-bottom:3px double #333; padding-bottom:5px; margin-bottom:15px;">
                        <h3 style="margin:0;">FORMULIR PINJAMAN KOPERASI MULTI-UNIT BERJENJANG</h3>
                    </div>
                    <table style="width:100%; font-size:13px; margin-bottom:20px;">
                        <tr><td><b>Nama Pemohon</b></td><td>: {s['nama']} ({s.get('unit')} - {s.get('lantai')})</td></tr>
                        <tr><td><b>No Anggota</b></td><td>: {s['no_anggota']}</td></tr>
                        <tr><td><b>Nominal Dana</b></td><td>: <b>Rp {s['nominal']:,}</b></td></tr>
                        <tr><td><b>Keperluan</b></td><td>: {s['keperluan']}</td></tr>
                    </table>
                    <div style="display:table; width:100%; text-align:center; font-size:11px;">
                        <div style="display:table-row;">
                            <div style="display:table-cell; width:50%; padding-bottom:10px;">
                                <p style="margin:0 0 5px 0; font-weight:bold;">1. Pemohon (Anggota)</p>
                                <img src="data:image/png;base64,{s.get('ttd_pengaju','')}" style="height:60px; border:1px dashed #ccc;"/>
                            </div>
                            <div style="display:table-cell; width:50%; padding-bottom:10px;">
                                <p style="margin:0 0 5px 0; font-weight:bold;">2. Penjamin Istri/Keluarga</p>
                                <img src="data:image/png;base64,{s.get('ttd_keluarga','')}" style="height:60px; border:1px dashed #ccc;"/>
                            </div>
                        </div>
                        <div style="display:table-row;">
                            <div style="display:table-cell; width:50%; padding-bottom:10px;">
                                <p style="margin:0 0 5px 0; font-weight:bold;">3. Kepala Divisi Unit</p>
                                <img src="data:image/png;base64,{s.get('ttd_kadiv','')}" style="height:60px; border:1px dashed #ccc;"/>
                            </div>
                            <div style="display:table-cell; width:50%; padding-bottom:10px;">
                                <p style="margin:0 0 5px 0; font-weight:bold;">4. Kepala Bidang</p>
                                <img src="data:image/png;base64,{s.get('ttd_kabid','')}" style="height:60px; border:1px dashed #ccc;"/>
                            </div>
                        </div>
                        <div style="display:table-row;">
                            <div style="display:table-cell; width:50%;"></div>
                            <div style="display:table-cell; width:50%;">
                                <p style="margin:0 0 5px 0; font-weight:bold;">5. Direktur Koperasi</p>
                                <img src="data:image/png;base64,{s.get('ttd_direktur','')}" style="height:60px; border:1px dashed #ccc;"/>
                            </div>
                        </div>
                    </div>
                </div>
                <script>setTimeout(function(){{ window.print(); }}, 800);</script>
                """
                st.components.v1.html(html_template, height=450, scrolling=True)

    # TAB 2: OTORISASI VALIDASI RESET PASSWORD PEJABAT
    with tab2:
        st.subheader("🔐 Permintaan Reset Password Pejabat Masuk")
        st.write("Berikut adalah daftar akun Kepala Divisi/Pejabat yang terkunci karena lupa password. Silakan lakukan konfirmasi fisik/lisan sebelum meng-ACC password baru mereka.")
        
        pejabat_reset = [u for u in data_saat_ini["users"] if u.get("status_akun") == "Menunggu Reset"]
        
        if not pejabat_reset:
            st.info("Aman! Tidak ada permintaan reset password pejabat saat ini.")
            
        for u_pej in pejabat_reset:
            st.warning(f"⚠️ **Akun: {u_pej['username']}** — Nama: *{u_pej['nama']}* ({u_pej['unit']} - {u_pej['lantai']})")
            st.write("Status: **Terkunci (Minta Reset Password Baru)**")
            
            c_res1, c_res2 = st.columns(2)
            with c_res1:
                if st.button(f"✅ Setujui & Aktifkan Password Baru ({u_pej['username']})"):
                    u_pej["password"] = u_pej["password_baru"]  # Ganti password lama dengan password baru
                    u_pej["password_baru"] = ""
                    u_pej["status_akun"] = "Aktif"  # Buka gembok akun
                    
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Approved Reset: {u_pej['username']}"):
                        st.success(f"✅ Akun {u_pej['username']} berhasil diaktifkan dengan password baru!")
                        time.sleep(1.2); st.rerun()
            with c_res2:
                if st.button(f"❌ Tolak / Batalkan Reset ({u_pej['username']})"):
                    u_pej["password_baru"] = ""
                    u_pej["status_akun"] = "Aktif"  # Kembalikan ke password lama saja
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Tolak Reset: {u_pej['username']}"):
                        st.error("Permintaan reset ditolak, akun dikembalikan ke status normal.")
                        time.sleep(1.2); st.rerun()
