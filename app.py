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
            data = json.loads(content_decoded)
            return data, file_content["sha"]
    return TEMPLATE_AWAL, None

def push_database_to_github(updated_data, sha_lama, message):
    json_string = json.dumps(updated_data, indent=4, ensure_ascii=False)
    content_encoded = base64.b64encode(json_string.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{DB_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Content-Type": "application/json"}
    payload = {"message": message, "content": content_encoded, "sha": sha_lama}
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
    st.info("Silakan login di sidebar untuk melanjutkan.")
else:
    st.title(f"Akses: {role}")

    # ---------------------------------------------------------------------
    # 📝 USER BIASA (PENGAJU)
    # ---------------------------------------------------------------------
    if role == "User Biasa":
        with st.form("form_pengajuan"):
            nama = st.text_input("Nama Lengkap")
            no_anggota = st.text_input("No Anggota")
            nominal = st.number_input("Nominal", min_value=0)
            keperluan = st.text_area("Keperluan")
            st.write("Tanda Tangan Pengaju:")
            cv_user = st_canvas(stroke_width=3, height=150, width=300, key="cv_user")
            if st.form_submit_button("Kirim Pengajuan"):
                ttd_user = canvas_to_base64(cv_user.image_data)
                if nama and ttd_user:
                    new_data = {
                        "nama": nama, "no_anggota": no_anggota, "nominal": nominal, "keperluan": keperluan,
                        "ttd_pengaju": ttd_user, "status": "Menunggu Divisi"
                    }
                    data_saat_ini["database"].append(new_data)
                    push_database_to_github(data_saat_ini, sha_saat_ini, f"Baru: {nama}")
                    st.success("Terkirim!"); st.rerun()

    # ---------------------------------------------------------------------
    # ✅ KEPALA DIVISI
    # ---------------------------------------------------------------------
    elif role == "Kepala Divisi":
        items = [i for i in data_saat_ini["database"] if i.get("status") == "Menunggu Divisi"]
        if not items: st.info("Tidak ada data.")
        for idx, item in enumerate(items):
            with st.expander(f"Pengajuan {item['nama']}"):
                st.write(f"Nominal: Rp {item['nominal']:,}")
                st.write(f"Keperluan: {item['keperluan']}")
                st.write("---")
                st.write("Tanda Tangan Kepala Divisi di Sini:")
                cv_div = st_canvas(stroke_width=3, height=150, width=300, key=f"cv_div_{idx}")
                if st.button("Setujui & Tanda Tangan", key=f"btn_div_{idx}"):
                    ttd_div = canvas_to_base64(cv_div.image_data)
                    if ttd_div:
                        for d in data_saat_ini["database"]:
                            if d["no_anggota"] == item["no_anggota"] and d["status"] == "Menunggu Divisi":
                                d["status"] = "Menunggu Bidang"; d["ttd_kadiv"] = ttd_div
                        push_database_to_github(data_saat_ini, sha_saat_ini, "Setuju Kadiv")
                        st.rerun()

    # ---------------------------------------------------------------------
    # ✅ KEPALA BIDANG
    # ---------------------------------------------------------------------
    elif role == "Kepala Bidang":
        items = [i for i in data_saat_ini["database"] if i.get("status") == "Menunggu Bidang"]
        for idx, item in enumerate(items):
            with st.expander(f"Dari: {item['nama']}"):
                st.write(f"Nominal: Rp {item['nominal']:,}")
                st.write("Silakan Tanda Tangan Kepala Bidang:")
                cv_bid = st_canvas(stroke_width=3, height=150, width=300, key=f"cv_bid_{idx}")
                if st.button("Verifikasi Kepala Bidang", key=f"btn_bid_{idx}"):
                    ttd_bid = canvas_to_base64(cv_bid.image_data)
                    if ttd_bid:
                        for d in data_saat_ini["database"]:
                            if d["no_anggota"] == item["no_anggota"] and d["status"] == "Menunggu Bidang":
                                d["status"] = "Menunggu Direktur"; d["ttd_kabid"] = ttd_bid
                        push_database_to_github(data_saat_ini, sha_saat_ini, "Setuju Kabid")
                        st.rerun()

    # ---------------------------------------------------------------------
    # ✅ DIREKTUR
    # ---------------------------------------------------------------------
    elif role == "Direktur":
        items = [i for i in data_saat_ini["database"] if i.get("status") == "Menunggu Direktur"]
        for idx, item in enumerate(items):
            with st.expander(f"Persetujuan Direktur: {item['nama']}"):
                st.write(f"Nominal: Rp {item['nominal']:,}")
                st.write("Tanda Tangan Direktur:")
                cv_dir = st_canvas(stroke_width=3, height=150, width=300, key=f"cv_dir_{idx}")
                if st.button("Setujui (Direktur)", key=f"btn_dir_{idx}"):
                    ttd_dir = canvas_to_base64(cv_dir.image_data)
                    if ttd_dir:
                        for d in data_saat_ini["database"]:
                            if d["no_anggota"] == item["no_anggota"] and d["status"] == "Menunggu Direktur":
                                d["status"] = "Menunggu SDM"; d["ttd_direktur"] = ttd_dir
                        push_database_to_github(data_saat_ini, sha_saat_ini, "Setuju Direktur")
                        st.rerun()

    # ---------------------------------------------------------------------
    # ✅ SDM (FINAL ACC & CETAK)
    # ---------------------------------------------------------------------
    elif role == "SDM":
        items = [i for i in data_saat_ini["database"] if i.get("status") == "Menunggu SDM"]
        for idx, item in enumerate(items):
            with st.expander(f"Final ACC: {item['nama']}"):
                st.write(f"Nama: {item['nama']} | Nominal: Rp {item['nominal']:,}")
                st.write(f"Keperluan: {item['keperluan']}")
                
                # SDM Bisa Lihat TTD Pengaju untuk verifikasi terakhir
                st.write("TTD Pengaju (Anggota):")
                st.image(base64.b64decode(item["ttd_pengaju"]), width=200)

                if st.button("ACC FINAL (SDM)", key=f"btn_sdm_{idx}"):
                    for d in data_saat_ini["database"]:
                        if d["no_anggota"] == item["no_anggota"] and d["status"] == "Menunggu SDM":
                            d["status"] = "SELESAI"
                    push_database_to_github(data_saat_ini, sha_saat_ini, "Final SDM")
                    st.success("Proses Selesai!"); st.rerun()

        st.write("---")
        st.subheader("🖨️ Riwayat Selesai (Siap Cetak)")
        selesai = [i for i in data_saat_ini["database"] if i.get("status") == "SELESAI"]
        for s in selesai:
            st.write(f"✅ {s['nama']} - Rp {s['nominal']:,}")
            # Cetak PDF Text sederhana
            txt_report = f"FORMULIR PINJAMAN\nNama: {s['nama']}\nNominal: {s['nominal']}\nStatus: TERVERIFIKASI SEMUA PIHAK"
            st.download_button(f"Unduh Form {s['nama']}", txt_report, file_name=f"{s['nama']}.txt")
