import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import json
import base64
import io
import requests

st.set_page_config(page_title="Form Pinjaman Koperasi", layout="centered")

# =========================================================
# KONFIGURASI GITHUB MAS LIAN
# =========================================================
GITHUB_USERNAME = "operansangiang-rs"
GITHUB_REPO = "koperasi.sng-app"
DATASTORE_FILE = "data_store.json"

# Gantilah teks di bawah ini dengan token ghp_... milik Mas Lian
GITHUB_TOKEN = "MASUKKAN_TOKEN_GITHUB_MAS_LIAN_DI_SINI" 
# =========================================================

TEMPLATE_AWAL = {
    "database": [],
    "categories": [
        "Pinjaman Rutin",
        "Pinjaman Darurat",
        "Pinjaman Modal Usaha"
    ]
}

# Fungsi Membaca Data Langsung dari GitHub API
def load_data_from_github():
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{DATASTORE_FILE}"
    
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
            return json.loads(content_decoded), file_content["sha"]
        except Exception:
            return TEMPLATE_AWAL, file_content.get("sha", None)
    else:
        return TEMPLATE_AWAL, None

# Fungsi Menyimpan Data dan Commit Otomatis ke GitHub
def save_data_to_github(nama, no_anggota, nominal, keperluan, kategori, ttd_base64):
    data_lama, sha_lama = load_data_from_github()
    
    entri_baru = {
        "nama": nama,
        "no_anggota": no_anggota,
        "nominal": int(nominal),
        "keperluan": keperluan,
        "kategori": kategori,
        "tanda_tangan_base64": ttd_base64
    }
    data_lama["database"].append(entri_baru)
    
    if kategori not in data_lama["categories"]:
        data_lama["categories"].append(kategori)
        
    json_string = json.dumps(data_lama, indent=4, ensure_ascii=False)
    content_encoded = base64.b64encode(json_string.encode("utf-8")).decode("utf-8")
    
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{DATASTORE_FILE}"
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": f"Update data_store.json: Pengajuan baru dari {nama}",
        "content": content_encoded
    }
    
    if sha_lama:
        payload["sha"] = sha_lama
        
    res = requests.put(url, headers=headers, json=payload)
    if res.status_code in [200, 201]:
        return True
    else:
        raise Exception(f"Gagal push ke GitHub: {res.text}")

st.title("🏛️ Pengajuan Pinjaman Koperasi")
st.write("Silakan isi formulir di bawah ini dengan lengkap dan benar.")

# Mengambil list kategori secara real-time dari GitHub
try:
    data_saat_ini, _ = load_data_from_github()
    categories_list = data_saat_ini["categories"]
except Exception:
    categories_list = TEMPLATE_AWAL["categories"]

# 1. FORMULIR INPUT DATA ANGGOTA KOPERASI
with st.form("form_pinjaman"):
    nama = st.text_input("Nama Lengkap Anggota")
    no_anggota = st.text_input("Nomor Anggota Koperasi")
    nominal = st.number_input("Nominal Pinjaman (Rp)", min_value=100000, step=50000)
    keperluan = st.text_area("Alasan/Keperluan Pinjaman")
    
    kategori = st.selectbox("Jenis Kategori Pinjaman", categories_list)
    kategori_baru = st.text_input("Atau ketik kategori baru di sini (Kosongkan jika tidak ada)")
    
    st.write("---")
    st.write("**Pernyataan:** Dengan menandatangani di bawah ini, saya menyatakan data di atas adalah benar.")
    
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

# 2. PROSES SIMPAN LANGSUNG KE GITHUB
if submit_button:
    kategori_final = kategori_baru.strip() if kategori_baru.strip() else kategori
    
    if not nama.strip() or not no_anggota.strip():
        st.error("❌ Mohon isi Nama dan Nomor Anggota terlebih dahulu!")
    elif canvas_result.image_data is None:
        st.error("❌ Tanda tangan wajib diisi!")
    else:
        with st.spinner("Sedang memproses dan mengunci data langsung ke GitHub..."):
            try:
                # Mengonversi gambar TTD menjadi Teks Base64
                img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                # Eksekusi simpan & push otomatis ke GitHub via API
                sukses = save_data_to_github(nama.strip(), no_anggota.strip(), nominal, keperluan.strip(), kategori_final.strip(), img_str)
                
                if sukses:
                    st.success("✅ Sukses! Data pengajuan berhasil dikirim dan diperbarui di GitHub.")
                    st.rerun()
                
            except Exception as e:
                st.error(f"Terjadi kesalahan sinkronisasi GitHub: {e}")
