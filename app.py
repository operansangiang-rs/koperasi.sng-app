import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import json
import os
import base64
import io

st.set_page_config(page_title="Form Pinjaman Koperasi", layout="centered")

# NAMA FILE DATABASE JSON
DATASTORE_FILE = "data_store.json"

# Struktur Awal Sesuai Contoh Mas Lian (Agar Tidak Kosong Sejak Awal)
TEMPLATE_AWAL = {
    "database": [],
    "categories": [
        "Pinjaman Rutin",
        "Pinjaman Darurat",
        "Pinjaman Modal Usaha"
    ]
}

# Fungsi Membaca Data & Otomatis Bikin File Jika Belum Ada
def load_data():
    if not os.path.exists(DATASTORE_FILE) or os.stat(DATASTORE_FILE).st_size == 0:
        with open(DATASTORE_FILE, "w", encoding="utf-8") as f:
            json.dump(TEMPLATE_AWAL, f, indent=4, ensure_ascii=False)
        return TEMPLATE_AWAL
        
    try:
        with open(DATASTORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "database" not in data: data["database"] = []
            if "categories" not in data: data["categories"] = []
            return data
    except Exception:
        return TEMPLATE_AWAL

# Fungsi Menambah Data Pengajuan Koperasi (Sistem Append)
def save_data(nama, no_anggota, nominal, keperluan, kategori, ttd_base64):
    data_lama = load_data()
    
    # Masukkan entri baru ke dalam list "database"
    entri_baru = {
        "nama": nama,
        "no_anggota": no_anggota,
        "nominal": int(nominal),
        "keperluan": keperluan,
        "kategori": kategori,
        "tanda_tangan_base64": ttd_base64
    }
    data_lama["database"].append(entri_baru)
    
    # Masukkan kategori ke list categories jika ada tipe baru yang diketik
    if kategori not in data_lama["categories"]:
        data_lama["categories"].append(kategori)
        
    with open(DATASTORE_FILE, "w", encoding="utf-8") as f:
        json.dump(data_lama, f, indent=4, ensure_ascii=False)

# Pancing fungsi load_data di awal agar file otomatis tercipta di folder
data_saat_ini = load_data()

st.title("🏛️ Pengajuan Pinjaman Koperasi")
st.write("Silakan isi formulir di bawah ini dengan lengkap dan benar.")

# 1. FORMULIR INPUT DATA ANGGOTA KOPERASI
with st.form("form_pinjaman"):
    nama = st.text_input("Nama Lengkap Anggota")
    no_anggota = st.text_input("Nomor Anggota Koperasi")
    nominal = st.number_input("Nominal Pinjaman (Rp)", min_value=100000, step=50000)
    keperluan = st.text_area("Alasan/Keperluan Pinjaman")
    
    # Kategori Pinjaman diambil dari list "categories" di JSON
    kategori = st.selectbox("Jenis Kategori Pinjaman", data_saat_ini["categories"])
    kategori_baru = st.text_input("Atau ketik kategori baru di sini (Kosongkan jika tidak ada)")
    
    st.write("---")
    st.write("**Pernyataan:** Dengan menandatangani di bawah ini, saya menyatakan data di atas adalah benar.")
    
    # KANVAS TANDA TANGAN
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

# 2. PROSES SIMPAN KE FILE data_store.json
if submit_button:
    kategori_final = kategori_baru.strip() if kategori_baru.strip() else kategori
    
    if not nama.strip() or not no_anggota.strip():
        st.error("❌ Mohon isi Nama dan Nomor Anggota terlebih dahulu!")
    elif canvas_result.image_data is None:
        st.error("❌ Tanda tangan wajib diisi!")
    else:
        try:
            # Mengonversi coretan gambar TTD menjadi Teks Base64
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # Eksekusi simpan data ke struktur JSON yang rapi
            save_data(nama.strip(), no_anggota.strip(), nominal, keperluan.strip(), kategori_final.strip(), img_str)
            
            st.success("✅ Sukses! Data pendaftaran Anda berhasil dikirim.")
            st.rerun()
            
        except Exception as e:
            st.error(f"Terjadi kesalahan sistem: {e}")
