import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import pandas as pd
import os

st.set_page_config(page_title="Form Pinjaman Koperasi", layout="centered")

st.title("🏛️ Pengajuan Pinjaman Koperasi")
st.write("Silakan isi formulir di bawah ini dengan benar.")

# 1. FORMULIR INPUT DATA ANGOTA
with st.form("form_pinjaman"):
    nama = st.text_input("Nama Lengkap Anggota")
    no_anggota = st.text_input("Nomor Anggota Koperasi")
    nominal = st.number_input("Nominal Pinjaman (Rp)", min_value=100000, step=50000)
    keperluan = st.text_area("Alasan/Keperluan Pinjaman")
    
    st.write("---")
    st.write("**Pernyataan:** Dengan menandatangani di bawah ini, saya menyatakan data di atas adalah benar.")
    
    # 2. KANVAS TANDA TANGAN (Bisa di-touchscreen HP atau digeser Mouse)
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)", 
        stroke_width=3,
        stroke_color="#000000", # Warna tinta hitam
        background_color="#ffffff", # Kotak warna putih
        height=150,
        width=350,
        drawing_mode="freedraw",
        key="canvas_ttd",
    )
    
    # Tombol Kirim Form
    submit_button = st.form_submit_button("Kirim Pengajuan")

# 3. PROSES SIMPAN DATA SETELAH TOMBOL DIKLIK
if submit_button:
    if not nama or not no_anggota or nominal == 0:
        st.error("❌ Mohon isi semua data formulir terlebih dahulu!")
    elif canvas_result.image_data is None:
        st.error("❌ Tanda tangan wajib diisi!")
    else:
        st.success("✅ Pengajuan Berhasil Dikirim!")
        
        # Simpan teks formulir ke file Excel/CSV sederhana
        data_baru = {"Nama": [nama], "No Anggota": [no_anggota], "Nominal": [nominal], "Keperluan": [keperluan]}
        df = pd.DataFrame(data_baru)
        
        # Simpan Tanda Tangan sebagai File PNG (Diberi nama berdasarkan No Anggota)
        img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
        nama_file_ttd = f"ttd_{no_anggota}.png"
        img.save(nama_file_ttd)
        
        st.write(f"File tanda tangan disimpan dengan nama: `{nama_file_ttd}`")
        st.image(img, caption="Pratinjau Tanda Tangan Anda")
