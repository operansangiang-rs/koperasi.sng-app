import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import pandas as pd
import json
import os
import base64
import io

st.set_page_config(page_title="Form Pinjaman Koperasi", layout="centered")

# Nama file database JSON
DATASTORE_FILE = "data_store.json"

# Fungsi Membaca Data
def load_data():
    if os.path.exists(DATASTORE_FILE):
        try:
            with open(DATASTORE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

# Fungsi Menambah Data (Append)
def save_data(data_baru):
    data_lama = load_data()          
    data_lama.append(data_baru)       
    with open(DATASTORE_FILE, "w", encoding="utf-8") as f:
        json.dump(data_lama, f, indent=4, ensure_ascii=False)

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
            
            # Buat paket data
            entri_baru = {
                "nama": nama,
                "no_anggota": no_anggota,
                "nominal": int(nominal),
                "keperluan": keperluan,
                "tanda_tangan_base64": img_str  # TTD tetap disimpan aman di dalam file JSON
            }
            
            # Eksekusi simpan
            save_data(entri_baru)
            st.success("✅ Sukses! Data pendaftaran berhasil dikunci ke data_store.json!")
            
        except Exception as e:
            st.error(f"Terjadi kesalahan sistem: {e}")

# 3. MONITOR DATA (YANG DITAMPILKAN DI WEB HANYA YANG RAPI SAJA)
st.write("---")
st.subheader("📊 Daftar Riwayat Pengajuan Koperasi")

data_tercatat = load_data()

if data_tercatat:
    # Buat salinan data untuk tampilan layar saja
    data_tampilan_layar = []
    for item in data_tercatat:
        data_tampilan_layar.append({
            "Nama": item["nama"],
            "No Anggota": item["no_anggota"],
            "Nominal (Rp)": item["nominal"],
            "Keperluan": item["keperluan"]
        })
    
    # Tampilkan dalam bentuk tabel rapi (Tanpa kode teks tulisan aneh tadi)
    df_tampil = pd.DataFrame(data_tampilan_layar)
    st.dataframe(df_tampil, use_container_width=True)
    
    # BONUS: Tampilkan Gambar Tanda Tangan Terakhir yang baru saja diinput
    st.write("**Pratinjau Tanda Tangan Terakhir:**")
    try:
        last_ttd_base64 = data_tercatat[-1]["tanda_tangan_base64"]
        msg = base64.b64decode(last_ttd_base64)
        buf = io.BytesIO(msg)
        img_preview = Image.open(buf)
        st.image(img_preview, width=200)
    except Exception:
        pass

    # Tombol download file aslinya tetap ada jika Mas Lian butuh untuk dipindahkan
    json_string = json.dumps(data_tercatat, indent=4, ensure_ascii=False)
    st.download_button(
        label="📥 Download Database data_store.json",
        data=json_string,
        file_name="data_store.json",
        mime="application/json"
    )
else:
    st.info("Belum ada data pengajuan yang masuk.")
