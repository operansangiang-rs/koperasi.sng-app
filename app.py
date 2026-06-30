import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import json
import base64
import io
import requests

st.set_page_config(page_title="Sistem Approval Berjenjang Koperasi", layout="centered")

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
TEMPLATE_AWAL = {"database": [], "categories": ["Pinjaman Rutin", "Pinjaman Darurat", "Pinjaman Modal Usaha"]}

# --- Fungsi Helper: Konversi Canvas ke Base64 ---
def canvas_to_base64(canvas_data):
    if canvas_data is not None:
        # Periksa apakah ada goresan tanda tangan di kanvas
        if canvas_data.any():
            img = Image.fromarray(canvas_data.astype('uint8'), 'RGBA')
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode()
    return None

# --- Fungsi API GitHub ---
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
                if "categories" not in data: data["categories"] = []
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
# 🔑 LOGIN SYSTEM
# =========================================================================
st.sidebar.title("🔐 Login Pejabat")
role = st.sidebar.selectbox("Pilih Role", ["User Biasa", "Kepala Divisi", "Kepala Bidang", "Direktur", "SDM"])

login_sukses = False
if role == "User Biasa": login_sukses = True
elif role == "Kepala Divisi" and st.sidebar.text_input("Pass", type="password") == "123": login_sukses = True
elif role == "Kepala Bidang" and st.sidebar.text_input("Pass", type="password") == "1234": login_sukses = True
elif role == "Direktur" and st.sidebar.text_input("Pass", type="password") == "12345": login_sukses = True
elif role == "SDM" and st.sidebar.text_input("Pass", type="password") == "123456": login_sukses = True

if not login_sukses:
    st.info("👋 Silakan masukkan password valid di sidebar kiri.")
else:
    st.title(f"🏛️ Portal Koperasi - Akses: {role}")
    st.write("---")

    # ---------------------------------------------------------------------
    # 📝 USER BIASA (PENGAJU)
    # ---------------------------------------------------------------------
    if role == "User Biasa":
        with st.form("form_pengajuan"):
            nama = st.text_input("Nama Lengkap")
            no_anggota = st.text_input("No Anggota")
            nominal = st.number_input("Nominal Pinjaman", min_value=0, step=50000)
            keperluan = st.text_area("Keperluan")
            st.write("Tanda Tangan Pengaju:")
            cv_user = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=150, width=300, key="cv_user")
            
            if st.form_submit_button("Kirim Pengajuan"):
                ttd_user = canvas_to_base64(cv_user.image_data)
                if not nama.strip() or not no_anggota.strip():
                    st.error("❌ Nama dan Nomor Anggota wajib diisi!")
                elif not ttd_user:
                    st.error("❌ Tanda tangan wajib diisi!")
                else:
                    new_data = {
                        "nama": nama.strip(), 
                        "no_anggota": no_anggota.strip(), 
                        "nominal": nominal, 
                        "keperluan": keperluan.strip(),
                        "ttd_pengaju": ttd_user, 
                        "status": "Menunggu Divisi",
                        "ttd_kadiv": "",
                        "ttd_kabid": "",
                        "ttd_direktur": ""
                    }
                    data_saat_ini["database"].append(new_data)
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Baru: {nama}"):
                        st.success("✅ Pengajuan berhasil dikirim!")
                        st.rerun()

    # ---------------------------------------------------------------------
    # ✅ KEPALA DIVISI
    # ---------------------------------------------------------------------
    elif role == "Kepala Divisi":
        items = [i for i in data_saat_ini["database"] if i.get("status", "Menunggu Divisi") == "Menunggu Divisi"]
        if not items: 
            st.info("Belum ada pengajuan baru yang memerlukan verifikasi Kepala Divisi.")
        for idx, item in enumerate(items):
            with st.expander(f"Pengajuan {item['nama']} - Rp {item['nominal']:,}"):
                st.write(f"**No Anggota:** {item['no_anggota']}")
                st.write(f"**Keperluan:** {item['keperluan']}")
                st.write("---")
                st.write("**Silakan Tanda Tangan Kepala Divisi untuk Menyetujui:**")
                cv_div = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=150, width=300, key=f"cv_div_{idx}")
                
                if st.button("Setujui & Tanda Tangan", key=f"btn_div_{idx}"):
                    ttd_div = canvas_to_base64(cv_div.image_data)
                    if not ttd_div:
                        st.error("❌ Anda wajib tanda tangan sebelum menyetujui!")
                    else:
                        # SIMPAN TTD KADIV LANGSUNG KE DALAM ITEM DATABASE
                        for d in data_saat_ini["database"]:
                            if d["no_anggota"] == item["no_anggota"] and d.get("status", "Menunggu Divisi") == "Menunggu Divisi":
                                d["status"] = "Menunggu Bidang"
                                d["ttd_kadiv"] = ttd_div  # Mengunci tanda tangan kadiv
                                break
                        if push_database_to_github(data_saat_ini, sha_saat_ini, f"Setuju Kadiv: {item['nama']}"):
                            st.success("✅ Berhasil disetujui! Dialihkan ke Kepala Bidang.")
                            st.rerun()

    # ---------------------------------------------------------------------
    # ✅ KEPALA BIDANG
    # ---------------------------------------------------------------------
    elif role == "Kepala Bidang":
        items = [i for i in data_saat_ini["database"] if i.get("status") == "Menunggu Bidang"]
        if not items: st.info("Tidak ada data yang menunggu verifikasi Kepala Bidang.")
        for idx, item in enumerate(items):
            with st.expander(f"Dari: {item['nama']} - Rp {item['nominal']:,}"):
                st.write(f"**No Anggota:** {item['no_anggota']}")
                st.write(f"**Keperluan:** {item['keperluan']}")
                st.write("---")
                st.write("**Silakan Tanda Tangan Kepala Bidang:**")
                cv_bid = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=150, width=300, key=f"cv_bid_{idx}")
                
                if st.button("Verifikasi Kepala Bidang", key=f"btn_bid_{idx}"):
                    ttd_bid = canvas_to_base64(cv_bid.image_data)
                    if not ttd_bid:
                        st.error("❌ Anda wajib tanda tangan!")
                    else:
                        for d in data_saat_ini["database"]:
                            if d["no_anggota"] == item["no_anggota"] and d.get("status") == "Menunggu Bidang":
                                d["status"] = "Menunggu Direktur"
                                d["ttd_kabid"] = ttd_bid  # Mengunci tanda tangan kabid
                                break
                        if push_database_to_github(data_saat_ini, sha_saat_ini, f"Setuju Kabid: {item['nama']}"):
                            st.success("✅ Berhasil disetujui Kabid! Dialihkan ke Direktur.")
                            st.rerun()

    # ---------------------------------------------------------------------
    # ✅ DIREKTUR
    # ---------------------------------------------------------------------
    elif role == "Direktur":
        items = [i for i in data_saat_ini["database"] if i.get("status") == "Menunggu Direktur"]
        if not items: st.info("Tidak ada data yang menunggu verifikasi Direktur.")
        for idx, item in enumerate(items):
            with st.expander(f"Persetujuan Direktur: {item['nama']}"):
                st.write(f"**Nominal:** Rp {item['nominal']:,}")
                st.write(f"**Keperluan:** {item['keperluan']}")
                st.write("---")
                st.write("**Tanda Tangan Direktur:**")
                cv_dir = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=150, width=300, key=f"cv_dir_{idx}")
                
                if st.button("Setujui (Direktur)", key=f"btn_dir_{idx}"):
                    ttd_dir = canvas_to_base64(cv_dir.image_data)
                    if not ttd_dir:
                        st.error("❌ Anda wajib tanda tangan!")
                    else:
                        for d in data_saat_ini["database"]:
                            if d["no_anggota"] == item["no_anggota"] and d.get("status") == "Menunggu Direktur":
                                d["status"] = "Menunggu SDM"
                                d["ttd_direktur"] = ttd_dir  # Mengunci tanda tangan direktur
                                break
                        if push_database_to_github(data_saat_ini, sha_saat_ini, f"Setuju Direktur: {item['nama']}"):
                            st.success("✅ Berhasil disetujui Direktur! Dialihkan ke SDM.")
                            st.rerun()

    # ---------------------------------------------------------------------
    # ✅ SDM (FINAL ACC & CETAK)
    # ---------------------------------------------------------------------
    elif role == "SDM":
        items = [i for i in data_saat_ini["database"] if i.get("status") == "Menunggu SDM"]
        if not items: st.info("Tidak ada pengajuan yang siap di-ACC.")
        for idx, item in enumerate(items):
            with st.expander(f"Final ACC: {item['nama']} - Rp {item['nominal']:,}"):
                st.write(f"**Nama:** {item['nama']} | **No Anggota:** {item['no_anggota']}")
                st.write(f"**Keperluan:** {item['keperluan']}")
                st.write("---")
                
                # SDM Bisa memantau & memverifikasi TTD Pengaju sebelum cetak
                st.write("**Lembar Tanda Tangan Pengaju (Anggota):**")
                if item.get("ttd_pengaju"):
                    st.image(base64.b64decode(item["ttd_pengaju"]), width=200)

                if st.button("ACC FINAL & NYATAKAN SELESAI", key=f"btn_sdm_{idx}"):
                    for d in data_saat_ini["database"]:
                        if d["no_anggota"] == item["no_anggota"] and d.get("status") == "Menunggu SDM":
                            d["status"] = "SELESAI"
                            break
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Final ACC SDM: {item['nama']}"):
                        st.success("Proses Selesai dan disimpan!"); st.rerun()

        st.write("---")
        st.subheader("🖨️ Riwayat Selesai (Siap Cetak Dokumen)")
        selesais = [i for i in data_saat_ini["database"] if i.get("status") == "SELESAI"]
        
        if not selesais:
            st.text("Belum ada formulir berkas yang berstatus SELESAI.")
        for idx, s in enumerate(selesais):
            with st.expander(f"📄 Berkas: {s['nama']} (Lengkap)"):
                st.write(f"Nama: {s['nama']}")
                st.write(f"Nominal: Rp {s['nominal']:,}")
                st.write(f"Status Pengajuan: **ACC SEPENUHNYA OLEH SEMUA PEJABAT**")
                
                # Tombol Download cetak berkas
                txt_report = f"=========================================\n" \
                             f"         FORMULIR PINJAMAN KOPERASI      \n" \
                             f"=========================================\n" \
                             f"Nama Anggota   : {s['nama']}\n" \
                             f"Nomor Anggota  : {s['no_anggota']}\n" \
                             f"Nominal        : Rp {s['nominal']:,}\n" \
                             f"Keperluan      : {s['keperluan']}\n\n" \
                             f"STATUS VERIFIKASI: VALID & SELESAI\n" \
                             f"-----------------------------------------\n" \
                             f"Tanda Tangan Pengaju   : [TERKUNCI: BASE64_DATA]\n" \
                             f"Tanda Tangan Kadiv     : [TERKUNCI: BASE64_DATA]\n" \
                             f"Tanda Tangan Kabid     : [TERKUNCI: BASE64_DATA]\n" \
                             f"Tanda Tangan Direktur  : [TERKUNCI: BASE64_DATA]\n" \
                             f"========================================="
                             
                st.download_button(f"📥 Unduh Form Dokumen {s['nama']}", txt_report, file_name=f"Form_Koperasi_{s['nama']}.txt", key=f"dl_{idx}")
