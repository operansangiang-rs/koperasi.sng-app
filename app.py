import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import pandas as pd
import json
import os
import base64
import io

st.set_page_config(page_title="Form Pinjaman Koperasi", layout="centered")

# 1. DEFINISI FILE STORAGE
DATASTORE_FILE = "datastore.json"

# Fungsi membaca data dari JSON (Supaya data lama tetap aman)
def load_data():
    if os.path.exists(DATASTORE_FILE):
        try:
            with open(DATASTORE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []  # Jika file rusak/kosong, kembalikan list kosong
    return []

# Fungsi menambahkan data baru tanpa menghapus data lama (APPEND SYSTEM)
def save_data(data_baru):
    data_lama = load_data()          # Ambil data lama dulu
    data_lama.append(data_baru)       # Masukkan data baru ke dalam list
    with open(DATASTORE_FILE, "w", encoding="utf-8") as f:
        json.dump(data_lama, f, indent=4, ensure_ascii=False) # Tulis kembali semuanya

st.title("🏛️ Pengajuan Pinjaman Koperasi")
st.write("Isi formulir di bawah. Data dijamin aman dan masuk ke basis data.")

# 2. FORMULIR INPUT DATA ANGGOTA
with st.form("form_pinjaman", clear_on_submit=True):
    nama = st.text_input("Nama Lengkap Anggota")
    no_anggota = st.text_input("Nomor Anggota Koperasi")
    nominal = st.number_input("Nominal Pinjaman (Rp)", min_value=100000, step=50000)
    keperluan = st.text_area("Alasan/Keperluan Pinjaman")
    
    st.write("---")
    st.write("**Pernyataan:** Dengan menandatangani di bawah ini, saya menyatakan data di atas adalah benar.")
    
    # KANVAS TANDA TANGAN TOUCHSCREEN
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

# 3. PROSES SIMPAN AMAN KE JSON SETELAH TOMBOL DIKLIK
if submit_button:
    if not nama or not no_anggota:
        st.error("❌ Mohon isi Nama dan Nomor Anggota terlebih dahulu!")
    elif canvas_result.image_data is None:
        st.error("❌ Tanda tangan wajib diisi!")
    else:
        try:
            # Mengonversi coretan gambar TTD menjadi Teks Base64 agar menyatu di JSON
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # Gabungkan semua data menjadi satu paket
            entri_baru = {
                "nama": nama,
                "no_anggota": no_anggota,
                "nominal": int(nominal),
                "keperluan": keperluan,
                "tanda_tangan_base64": img_str  # TTD aman menyatu di dalam berkas JSON
            }
            
            # Eksekusi simpan tanpa hapus data lama
            save_data(entri_baru)
            st.success("✅ Pengajuan berhasil dikunci secara permanen ke datastore.json!")
            
        except Exception as e:
            st.error(f"Terjadi kesalahan sistem: {e}")

# 4. MONITOR DATA (Hanya untuk melihat riwayat data yang masuk di bawah halaman)
st.write("---")
st.subheader("📊 Log Riwayat Pengajuan (Database JSON)")
data_tercatat = load_data()

if data_tercatat:
    # Tampilkan rangkuman teks ke dalam tabel Streamlit
    df_tampil = pd.DataFrame(data_tercatat)[["nama", "no_anggota", "nominal", "keperluan"]]
    st.dataframe(df_tampil)
else:
    st.info("Belum ada data pengajuan yang tersimpan di datastore.json.")
