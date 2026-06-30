import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import json
import base64
import io
import requests

st.set_page_config(page_title="Sistem Pengajuan & Approval Koperasi", layout="centered")

# =========================================================================
# 🔐 MENGAMBIL DATA REPO & TOKEN AMAN DARI STREAMLIT SECRETS
# =========================================================================
try:
    GITHUB_TOKEN = st.secrets["github"]["token"]
    REPO_NAME = st.secrets["github"]["repo"]
except Exception:
    GITHUB_TOKEN = ""
    REPO_NAME = ""

DB_FILE = "data_store.json"

TEMPLATE_AWAL = {
    "database": [],
    "categories": ["Pinjaman Rutin", "Pinjaman Darurat", "Pinjaman Modal Usaha"]
}

# Fungsi Membaca Data dari GitHub
def load_data_from_github():
    if GITHUB_TOKEN.startswith("ghp_") and "/" in REPO_NAME:
        url = f"https://api.github.com/repos/{REPO_NAME}/contents/{DB_FILE}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            file_content = response.json()
            content_decoded = base64.b64decode(file_content["content"]).decode("utf-8")
            if content_decoded.strip() == "":
                return TEMPLATE_AWAL, file_content.get("sha", None)
            try:
                data = json.loads(content_decoded)
                if "database" not in data: data["database"] = []
                if "categories" not in data: data["categories"] = []
                return data, file_content["sha"]
            except Exception:
                return TEMPLATE_AWAL, file_content.get("sha", None)
    return TEMPLATE_AWAL, None

# Fungsi Update/Push Database back to GitHub
def push_database_to_github(updated_data, sha_lama, commit_message):
    json_string = json.dumps(updated_data, indent=4, ensure_ascii=False)
    content_encoded = base64.b64encode(json_string.encode("utf-8")).decode("utf-8")
    
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{DB_FILE}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": commit_message,
        "content": content_encoded
    }
    if sha_lama:
        payload["sha"] = sha_lama
        
    res = requests.put(url, headers=headers, json=payload)
    return res.status_code in [200, 201]

# Load data & SHA di awal
data_saat_ini, sha_saat_ini = load_data_from_github()

# =========================================================================
# 🔑 MENU LOGIN DI SIDEBAR (SEBELAH KIRI)
# =========================================================================
st.sidebar.title("🔐 Menu Akses")
role = st.sidebar.selectbox("Pilih Hak Akses / Role", ["User Biasa", "Kepala Divisi", "Kepala Bidang", "Direktur", "SDM"])

login_sukses = False

if role == "User Biasa":
    login_sukses = True
elif role == "Kepala Divisi":
    pwd = st.sidebar.text_input("Password Kepala Divisi", type="password")
    if pwd == "123": login_sukses = True
    elif pwd: st.sidebar.error("❌ Password Salah")
elif role == "Kepala Bidang":
    pwd = st.sidebar.text_input("Password Kepala Bidang", type="password")
    if pwd == "1234": login_sukses = True
    elif pwd: st.sidebar.error("❌ Password Salah")
elif role == "Direktur":
    pwd = st.sidebar.text_input("Password Direktur", type="password")
    if pwd == "12345": login_sukses = True
    elif pwd: st.sidebar.error("❌ Password Salah")
elif role == "SDM":
    pwd = st.sidebar.text_input("Password SDM", type="password")
    if pwd == "123456": login_sukses = True
    elif pwd: st.sidebar.error("❌ Password Salah")


# =========================================================================
# HALAMAN UTAMA BERDASARKAN HAK AKSES
# =========================================================================
if not login_sukses:
    st.info("👋 Silakan masukkan password valid di sidebar kiri untuk mengakses sistem.")
else:
    st.title(f"🏛️ Portal Koperasi - Akses: {role}")
    st.write("---")

    # ---------------------------------------------------------------------
    # 📝 MODE 1: USER BIASA (MENGISI FORMULIR)
    # ---------------------------------------------------------------------
    if role == "User Biasa":
        st.subheader("📝 Formulir Pengajuan Baru")
        
        with st.form("form_pinjaman"):
            nama = st.text_input("Nama Lengkap Anggota")
            no_anggota = st.text_input("Nomor Anggota Koperasi")
            nominal = st.number_input("Nominal Pinjaman (Rp)", min_value=100000, step=50000)
            keperluan = st.text_area("Alasan/Keperluan Pinjaman")
            kategori = st.selectbox("Jenis Kategori Pinjaman", data_saat_ini["categories"])
            
            st.write("---")
            st.write("**Pernyataan:** Dengan menandatangani di bawah ini, saya menyatakan data di atas adalah benar.")
            
            # Kanvas Tanda Tangan
            canvas_result = st_canvas(
                fill_color="rgba(255, 255, 255, 0)", 
                stroke_width=3,
                stroke_color="#000000", 
                background_color="#ffffff", 
                height=150,
                width=350,
                drawing_mode="freedraw",
                key="canvas_ttd",
            )
            
            submit_button = st.form_submit_button("Kirim Pengajuan")

        if submit_button:
            if not nama.strip() or not no_anggota.strip():
                st.error("❌ Mohon isi Nama dan Nomor Anggota terlebih dahulu!")
            elif canvas_result.image_data is None:
                st.error("❌ Tanda tangan wajib diisi!")
            else:
                with st.spinner("Sedang memproses dan mengunci data ke sistem..."):
                    try:
                        img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                        buffered = io.BytesIO()
                        img.save(buffered, format="PNG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        
                        # Paket data awal masuk
                        data_baru = {
                            "nama": nama.strip(),
                            "no_anggota": no_anggota.strip(),
                            "nominal": nominal,
                            "keperluan": keperluan.strip(),
                            "kategori": kategori,
                            "tanda_tangan_base64": img_str,
                            "status": "Menunggu Persetujuan Kepala Divisi"
                        }
                        
                        data_saat_ini["database"].append(data_baru)
                        
                        sukses = push_database_to_github(
                            data_saat_ini, 
                            sha_saat_ini, 
                            f"Pengajuan baru: {nama.strip()}"
                        )
                        
                        if sukses:
                            st.success("✅ Sukses! Pengajuan berhasil dikirim dan menunggu verifikasi.")
                            st.rerun()
                        else:
                            st.error("Gagal menyimpan ke database GitHub.")
                    except Exception as e:
                        st.error(f"Terjadi kesalahan sistem: {e}")

    # ---------------------------------------------------------------------
    # ✅ MODE 2: KEPALA DIVISI (VERIFIKASI TAHAP 1)
    # ---------------------------------------------------------------------
    elif role == "Kepala Divisi":
        st.subheader("☑️ Daftar Pengajuan Masuk (Verifikasi Kepala Divisi)")
        
        pengajuan_divisi = [item for item in data_saat_ini["database"] if item["status"] == "Menunggu Persetujuan Kepala Divisi"]
        
        if not pengajuan_divisi:
            st.info("Belum ada pengajuan yang memerlukan verifikasi Kepala Divisi.")
        else:
            for idx, item in enumerate(pengajuan_divisi):
                with st.expander(f"Pengajuan: {item['nama']} - Rp {item['nominal']:,}"):
                    st.write(f"**Nomor Anggota:** {item['no_anggota']}")
                    st.write(f"**Kategori:** {item['kategori']}")
                    st.write(f"**Keperluan:** {item['keperluan']}")
                    
                    st.write("**Tanda Tangan Pengaju:**")
                    try:
                        img_bytes = base64.b64decode(item["tanda_tangan_base64"])
                        img = Image.open(io.BytesIO(img_bytes))
                        st.image(img, width=250)
                    except Exception:
                        st.text("Gagal memuat gambar tanda tangan.")
                        
                    if st.button("Setujui Pengajuan Ini", key=f"app1_{idx}"):
                        # Update status ke tahap selanjutnya
                        for original_item in data_saat_ini["database"]:
                            if original_item["no_anggota"] == item["no_anggota"] and original_item["status"] == "Menunggu Persetujuan Kepala Divisi":
                                original_item["status"] = "Menunggu Persetujuan Kepala Bidang"
                                break
                        
                        if push_database_to_github(data_saat_ini, sha_saat_ini, f"Disetujui Kadiv: {item['nama']}"):
                            st.success("✅ Berhasil disetujui! Status dialihkan ke Kepala Bidang.")
                            st.rerun()

    # ---------------------------------------------------------------------
    # ✅ MODE 3: KEPALA BIDANG (VERIFIKASI TAHAP 2)
    # ---------------------------------------------------------------------
    elif role == "Kepala Bidang":
        st.subheader("☑️ Daftar Verifikasi Kepala Bidang")
        
        pengajuan_kabid = [item for item in data_saat_ini["database"] if item["status"] == "Menunggu Persetujuan Kepala Bidang"]
        
        if not pengajuan_kabid:
            st.info("Tidak ada data yang menunggu verifikasi Kepala Bidang.")
        else:
            for idx, item in enumerate(pengajuan_kabid):
                with st.expander(f"Pengajuan: {item['nama']} - Rp {item['nominal']:,}"):
                    st.write(f"**Nomor Anggota:** {item['no_anggota']}")
                    st.write(f"**Kategori:** {item['kategori']}")
                    st.write(f"**Keperluan:** {item['keperluan']}")
                    
                    if st.button("Setujui Pengajuan Ini (Kabid)", key=f"app2_{idx}"):
                        for original_item in data_saat_ini["database"]:
                            if original_item["no_anggota"] == item["no_anggota"] and original_item["status"] == "Menunggu Persetujuan Kepala Bidang":
                                original_item["status"] = "Menunggu Persetujuan Direktur"
                                break
                                
                        if push_database_to_github(data_saat_ini, sha_saat_ini, f"Disetujui Kabid: {item['nama']}"):
                            st.success("✅ Berhasil disetujui Kabid! Status dialihkan ke Direktur.")
                            st.rerun()

    # ---------------------------------------------------------------------
    # ✅ MODE 4: DIREKTUR (VERIFIKASI TAHAP 3)
    # ---------------------------------------------------------------------
    elif role == "Direktur":
        st.subheader("☑️ Daftar Verifikasi Direktur")
        
        pengajuan_dir = [item for item in data_saat_ini["database"] if item["status"] == "Menunggu Persetujuan Direktur"]
        
        if not pengajuan_dir:
            st.info("Tidak ada data yang menunggu verifikasi Direktur.")
        else:
            for idx, item in enumerate(pengajuan_dir):
                with st.expander(f"Pengajuan: {item['nama']} - Rp {item['nominal']:,}"):
                    st.write(f"**Nomor Anggota:** {item['no_anggota']}")
                    st.write(f"**Kategori:** {item['kategori']}")
                    st.write(f"**Keperluan:** {item['keperluan']}")
                    
                    if st.button("Setujui Pengajuan Ini (Direktur)", key=f"app3_{idx}"):
                        for original_item in data_saat_ini["database"]:
                            if original_item["no_anggota"] == item["no_anggota"] and original_item["status"] == "Menunggu Persetujuan Direktur":
                                original_item["status"] = "Menunggu ACC SDM"
                                break
                                
                        if push_database_to_github(data_saat_ini, sha_saat_ini, f"Disetujui Direktur: {item['nama']}"):
                            st.success("✅ Berhasil disetujui Direktur! Status dialihkan ke ACC SDM.")
                            st.rerun()

    # ---------------------------------------------------------------------
    # ✅ MODE 5: SDM (FINALISASI ACC & CETAK PDF)
    # ---------------------------------------------------------------------
    elif role == "SDM":
        st.subheader("🏁 Finalisasi ACC & Cetak PDF (SDM)")
        
        pengajuan_sdm = [item for item in data_saat_ini["database"] if item["status"] == "Menunggu ACC SDM"]
        
        if not pengajuan_sdm:
            st.info("Tidak ada pengajuan yang siap di-ACC.")
        else:
            for idx, item in enumerate(pengajuan_sdm):
                with st.expander(f"Pengajuan: {item['nama']} - Rp {item['nominal']:,}"):
                    st.write(f"**Nomor Anggota:** {item['no_anggota']}")
                    st.write(f"**Kategori:** {item['kategori']}")
                    st.write(f"**Keperluan:** {item['keperluan']}")
                    
                    st.write("**Tanda Tangan Pengaju:**")
                    try:
                        img_bytes = base64.b64decode(item["tanda_tangan_base64"])
                        img = Image.open(io.BytesIO(img_bytes))
                        st.image(img, width=250)
                    except Exception:
                        pass
                        
                    # Tombol ACC Final
                    if st.button("ACC Akhir & Selesai", key=f"acc_{idx}"):
                        for original_item in data_saat_ini["database"]:
                            if original_item["no_anggota"] == item["no_anggota"] and original_item["status"] == "Menunggu ACC SDM":
                                original_item["status"] = "Sudah Di-ACC SDM"
                                break
                                
                        if push_database_to_github(data_saat_ini, sha_saat_ini, f"Di-ACC SDM: {item['nama']}"):
                            st.success("✅ Dokumen telah di-ACC sepenuhnya!")
                            st.rerun()
                            
                    # Tautan Cetak PDF Sederhana
                    st.write("---")
                    st.markdown("### 🖨️ Cetak Formulir")
                    pdf_data = f"Nama: {item['nama']}\nNominal: {item['nominal']}\nKeperluan: {item['keperluan']}\nStatus: ACC SEPENUHNYA OLEH SDM"
                    st.download_button(
                        label="📄 Download/Cetak Dokumen (TXT/PDF)",
                        data=pdf_data,
                        file_name=f"Form_Koperasi_{item['nama']}.txt",
                        mime="text/plain"
                    )
