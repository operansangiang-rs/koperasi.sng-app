import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import pandas as pd
import json
import os
import base64
import io

st.set_page_config(page_title="Form Pinjaman Koperasi", layout="centered")

# NAMA FILE SESUAI PERMINTAAN MAS LIAN
DATASTORE_FILE = "data_store.json"

# Fungsi Membaca Data (Mengamankan data yang sudah ada)
def load_data():
    if os.path.exists(DATASTORE_FILE):
        try:
            with open(DATASTORE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []  # Jika file kosongan/rusak, kembalikan list kosong
    return []

# Fungsi Menambah Data Baru ke Dalam File JSON (Sistem Append)
def save_data(data_baru):
    data_lama = load_data()          # Ambil isi data lama
    data_lama.append(data_baru)       # Tambah data baru ke baris paling bawah
    with open(DATASTORE_FILE, "w", encoding="utf-8") as f:
        json.dump(data_lama, f, indent=4, ensure_ascii=False) # Kunci balik ke file

st.title("🏛️ Pengajuan Pinjaman Koperasi")
st.write("Isi formulir di bawah. Data otomatis tersimpan langsung ke dalam file **data_store.json**.")

# 1. FORMULIR INPUT DATA ANGGOTA
with st.form("form_pinjaman", clear_on_submit=True):
    nama = st.text_input("Nama Lengkap Anggota")
    no_anggota = st.text_input("Nomor Anggota Koperasi")
    nominal = st.number_input("Nominal Pinjaman (Rp)", min_value=100000, step=50000)
    keperluan = st.text_area("Alasan/Keperluan Pinjaman")
    
    st.write("---")
    st.write("**Pernyataan:** Dengan menandatangani di bawah ini, saya menyatakan data di atas adalah benar.")
    
    # KANVAS TANDA TANGAN TOUCHSCREEN / MOUSE
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
    if not nama or not no_anggota:
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
            
            # Buat struktur objek datanya
            entri_baru = {
                "nama": nama,
                "no_anggota": no_anggota,
                "nominal": int(nominal),
                "keperluan": keperluan,
                "tanda_tangan_base64": img_str  # TTD menyatu dalam teks JSON
            }
            
            # Eksekusi sistem append
            save_data(entri_baru)
            st.success("✅ Sukses! Data pendaftaran berhasil dikunci ke data_store.json!")
            
        except Exception as e:
            st.error(f"Terjadi kesalahan sistem: {e}")

# 3. MENGINTIP ISI FILE data_store.json LANGSUNG DI BAWAH HALAMAN WEB
st.write("---")
st.subheader("📂 Isi File `data_store.json` (Muncul di Sini):")

data_tercatat = load_data()

if data_tercatat:
    # Mengubah format objek python menjadi string teks teks JSON rapi
    json_string = json.dumps(data_tercatat, indent=4, ensure_ascii=False)
    
    # Menampilkan teks mentah JSON dalam kotak kode di web Streamlit
    st.code(json_string, language="json")
    
    # Tombol instan untuk download file JSON langsung ke komputer/HP Anda dari browser
    st.download_button(
        label="📥 Download File data_store.json",
        data=json_string,
        file_name="data_store.json",
        mime="application/json"
    )
else:
    st.info("Belum ada data pengajuan yang masuk. File data_store.json masih kosong.")
