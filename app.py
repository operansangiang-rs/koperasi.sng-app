import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import json
import base64
import io
import requests
import time

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
        try:
            img = Image.fromarray(canvas_data.astype('uint8'), 'RGBA')
            if img.getbbox() is not None:
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                return base64.b64encode(buffered.getvalue()).decode()
        except Exception:
            pass
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
# 🔑 LOGIN SYSTEM & SESSION STATE
# =========================================================================
st.sidebar.title("🔐 Login Pejabat")
role = st.sidebar.selectbox("Pilih Role", ["User Biasa", "Kepala Divisi", "Kepala Bidang", "Direktur", "SDM"])

if "preview_data" not in st.session_state:
    st.session_state.preview_data = None

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
    # 📝 USER BIASA (PENGAJUAN) DENGAN TTD ISTRI / KELUARGA
    # ---------------------------------------------------------------------
    if role == "User Biasa":
        st.subheader("📝 Formulir Pengajuan Pinjaman")
        
        with st.form("form_pengajuan"):
            nama = st.text_input("Nama Lengkap")
            no_anggota = st.text_input("No Anggota")
            nominal = st.number_input("Nominal Pinjaman", min_value=0, step=50000)
            keperluan = st.text_area("Keperluan")
            
            # Pembagian Kolom Tanda Tangan biar rapi berdampingan
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
                elif not ttd_user:
                    st.error("❌ Tanda tangan Pemohon wajib diisi!")
                elif not ttd_keluarga:
                    st.error("❌ Tanda tangan Istri / Keluarga wajib diisi!")
                else:
                    st.session_state.preview_data = {
                        "nama": nama.strip(), 
                        "no_anggota": no_anggota.strip(), 
                        "nominal": nominal, 
                        "keperluan": keperluan.strip(),
                        "ttd_pengaju": ttd_user, 
                        "ttd_keluarga": ttd_keluarga, # Menyimpan ttd keluarga
                        "status": "Menunggu Divisi",
                        "ttd_kadiv": "", "ttd_kabid": "", "ttd_direktur": ""
                    }

        if st.session_state.preview_data is not None:
            p = st.session_state.preview_data
            st.warning("⚠️ **Konfirmasi Pratinjau Berkas Sebelum Dikirim**")
            st.info(f"**Nama:** {p['nama']} | **No Anggota:** {p['no_anggota']} | **Nominal:** Rp {p['nominal']:,}\n\n**Keperluan:** {p['keperluan']}")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✏️ Edit Kembali Data"):
                    st.session_state.preview_data = None
                    st.rerun()
            with c2:
                if st.button("🚀 Data Sudah Yakin, Kirim Berkas!"):
                    data_saat_ini["database"].append(p)
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Baru: {p['nama']}"):
                        st.success(f"✅ Sukses! Pengajuan {p['nama']} terkirim ke Kepala Divisi.")
                        st.toast("Data Berhasil Disimpan!", icon="💾")
                        st.session_state.preview_data = None
                        time.sleep(1.5)
                        st.rerun()

    # ---------------------------------------------------------------------
    # ✅ KEPALA DIVISI
    # ---------------------------------------------------------------------
    elif role == "Kepala Divisi":
        items = [i for i in data_saat_ini["database"] if i.get("status", "Menunggu Divisi") == "Menunggu Divisi"]
        if not items: 
            st.info("Belum ada pengajuan baru yang memerlukan verifikasi Kepala Divisi.")
        for idx, item in enumerate(items):
            st.markdown(f"### 📋 Pengajuan: {item['nama']} — Rp {item['nominal']:,}")
            st.write(f"**No Anggota:** {item['no_anggota']} | **Keperluan:** {item['keperluan']}")
            
            # Menampilkan TTD Pengaju dan Keluarga sebagai bahan pertimbangan Kadiv
            c_img1, c_img2 = st.columns(2)
            with c_img1:
                st.caption("Tanda Tangan Pemohon:")
                if item.get("ttd_pengaju"): st.image(base64.b64decode(item["ttd_pengaju"]), width=150)
            with c_img2:
                st.caption("Tanda Tangan Istri / Keluarga:")
                if item.get("ttd_keluarga"): st.image(base64.b64decode(item["ttd_keluarga"]), width=150)
                
            st.write("**Silakan Tanda Tangan Kepala Divisi untuk Menyetujui:**")
            cv_div = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=150, width=300, key=f"cv_div_{idx}")
            
            if st.button("✍️ Setujui & Kirim Tanda Tangan", key=f"btn_div_{idx}"):
                ttd_div = canvas_to_base64(cv_div.image_data)
                if not ttd_div:
                    st.error("❌ Anda wajib tanda tangan sebelum menyetujui!")
                else:
                    berhasil_update = False
                    for d in data_saat_ini["database"]:
                        if str(d["no_anggota"]).strip() == str(item["no_anggota"]).strip() and d.get("status") == "Menunggu Divisi":
                            d["status"] = "Menunggu Bidang"
                            d["ttd_kadiv"] = ttd_div
                            berhasil_update = True
                            break
                    
                    if berhasil_update and push_database_to_github(data_saat_ini, sha_saat_ini, f"Setuju Kadiv: {item['nama']}"):
                        st.success("✅ Berhasil disetujui! Berkas digeser ke Kepala Bidang.")
                        st.toast("Persetujuan Berhasil Disimpan!", icon="📝")
                        time.sleep(1.5)
                        st.rerun()
            st.write("---")

    # ---------------------------------------------------------------------
    # ✅ KEPALA BIDANG
    # ---------------------------------------------------------------------
    elif role == "Kepala Bidang":
        items = [i for i in data_saat_ini["database"] if i.get("status") == "Menunggu Bidang"]
        if not items: st.info("Tidak ada data yang menunggu verifikasi Kepala Bidang.")
        for idx, item in enumerate(items):
            st.markdown(f"### 📋 Dari: {item['nama']} — Rp {item['nominal']:,}")
            st.write(f"**No Anggota:** {item['no_anggota']} | **Keperluan:** {item['keperluan']}")
            st.write("**Silakan Tanda Tangan Kepala Bidang:**")
            
            cv_bid = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=150, width=300, key=f"cv_bid_{idx}")
            
            if st.button("✍️ Verifikasi & Tanda Tangan Kabid", key=f"btn_bid_{idx}"):
                ttd_bid = canvas_to_base64(cv_bid.image_data)
                if not ttd_bid:
                    st.error("❌ Anda wajib tanda tangan!")
                else:
                    berhasil_update = False
                    for d in data_saat_ini["database"]:
                        if str(d["no_anggota"]).strip() == str(item["no_anggota"]).strip() and d.get("status") == "Menunggu Bidang":
                            d["status"] = "Menunggu Direktur"
                            d["ttd_kabid"] = ttd_bid
                            berhasil_update = True
                            break
                    if berhasil_update and push_database_to_github(data_saat_ini, sha_saat_ini, f"Setuju Kabid: {item['nama']}"):
                        st.success("✅ Berhasil disetujui Kabid! Dialihkan ke Direktur.")
                        st.toast("Verifikasi Kabid Disimpan!", icon="💼")
                        time.sleep(1.5)
                        st.rerun()
            st.write("---")

    # ---------------------------------------------------------------------
    # ✅ DIREKTUR
    # ---------------------------------------------------------------------
    elif role == "Direktur":
        items = [i for i in data_saat_ini["database"] if i.get("status") == "Menunggu Direktur"]
        if not items: st.info("Tidak ada data yang menunggu verifikasi Direktur.")
        for idx, item in enumerate(items):
            st.markdown(f"### 📋 Persetujuan Direktur: {item['nama']} — Rp {item['nominal']:,}")
            st.write(f"**Keperluan:** {item['keperluan']}")
            st.write("**Tanda Tangan Direktur:**")
            
            cv_dir = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=150, width=300, key=f"cv_dir_{idx}")
            
            if st.button("✍️ Setujui (Direktur)", key=f"btn_dir_{idx}"):
                ttd_dir = canvas_to_base64(cv_dir.image_data)
                if not ttd_dir:
                    st.error("❌ Anda wajib tanda tangan!")
                else:
                    berhasil_update = False
                    for d in data_saat_ini["database"]:
                        if str(d["no_anggota"]).strip() == str(item["no_anggota"]).strip() and d.get("status") == "Menunggu Direktur":
                            d["status"] = "Menunggu SDM"
                            d["ttd_direktur"] = ttd_dir
                            berhasil_update = True
                            break
                    if berhasil_update and push_database_to_github(data_saat_ini, sha_saat_ini, f"Setuju Direktur: {item['nama']}"):
                        st.success("✅ Berhasil disetujui Direktur! Dialihkan ke SDM.")
                        st.toast("Persetujuan Direktur Disimpan!", icon="🏛️")
                        time.sleep(1.5)
                        st.rerun()
            st.write("---")

    # ---------------------------------------------------------------------
    # ✅ SDM (FINAL ACC & PRINT PDF LENGKAP)
    # ---------------------------------------------------------------------
    elif role == "SDM":
        if "print_id" not in st.session_state:
            st.session_state.print_id = None

        items = [i for i in data_saat_ini["database"] if i.get("status") == "Menunggu SDM"]
        if not items: st.info("Tidak ada pengajuan yang siap di-ACC.")
        for idx, item in enumerate(items):
            st.markdown(f"### 📋 Final ACC SDM: {item['nama']} — Rp {item['nominal']:,}")
            st.write(f"**No Anggota:** {item['no_anggota']} | **Keperluan:** {item['keperluan']}")
            
            c_sdm_img1, c_sdm_img2 = st.columns(2)
            with c_sdm_img1:
                st.write("**Tanda Tangan Pengaju:**")
                if item.get("ttd_pengaju"): st.image(base64.b64decode(item["ttd_pengaju"]), width=180)
            with c_sdm_img2:
                st.write("**Tanda Tangan Istri/Keluarga:**")
                if item.get("ttd_keluarga"): st.image(base64.b64decode(item["ttd_keluarga"]), width=180)

            if st.button("🔒 ACC FINAL & NYATAKAN SELESAI", key=f"btn_sdm_{idx}"):
                for d in data_saat_ini["database"]:
                    if str(d["no_anggota"]).strip() == str(item["no_anggota"]).strip() and d.get("status") == "Menunggu SDM":
                        d["status"] = "SELESAI"
                        break
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"Final ACC SDM: {item['nama']}"):
                    st.success("Proses Selesai dan disimpan secara permanen!"); 
                    st.toast("Status Berkas: SELESAI!", icon="🎉")
                    time.sleep(1.5)
                    st.rerun()
            st.write("---")

        st.write("---")
        st.subheader("🖨️ Riwayat Selesai (Siap Cetak PDF Resmi)")
        selesais = [i for i in data_saat_ini["database"] if i.get("status") == "SELESAI"]
        
        if not selesais:
            st.text("Belum ada berkas formulir berstatus SELESAI.")
        
        for idx, s in enumerate(selesais):
            col1, col2 = st.columns([4, 2])
            with col1:
                st.write(f"✅ **{s['nama']}** — Rp {s['nominal']:,}")
            with col2:
                if st.button("🖨️ Cetak Berkas PDF", key=f"print_btn_{idx}"):
                    st.session_state.print_id = s['no_anggota']

            if st.session_state.print_id == s['no_anggota']:
                st.write("---")
                if st.button("❌ Tutup / Batal Cetak", key=f"close_btn_{idx}"):
                    st.session_state.print_id = None
                    st.rerun()
                
                st.info(f"Tekan tombol printer bawaan laptop/HP Anda untuk menyimpannya sebagai **Save as PDF**.")
                
                # Desain PDF Output (Menampilkan Lembar TTD Pemohon + Istri/Keluarga secara Berdampingan)
                html_template = f"""
                <div id="print-area" style="padding: 25px; border: 2px solid #333; font-family: Arial, sans-serif; background-color: white; color: black; max-width: 700px; margin: auto;">
                    <div style="text-align: center; border-bottom: 3px double #333; padding-bottom: 10px; margin-bottom: 20px;">
                        <h2 style="margin: 0; text-transform: uppercase;">FORMULIR RESMI PINJAMAN KOPERASI</h2>
                        <p style="margin: 5px 0 0 0; font-size: 13px;">Sistem Otomasi Verifikasi Berjenjang Elektronik</p>
                    </div>
                    
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 25px;">
                        <tr><td style="width: 30%; padding: 6px 0; font-weight: bold;">Nama Lengkap</td><td style="width: 70%;">: {s['nama']}</td></tr>
                        <tr><td style="padding: 6px 0; font-weight: bold;">Nomor Anggota</td><td>: {s['no_anggota']}</td></tr>
                        <tr><td style="padding: 6px 0; font-weight: bold;">Nominal Dana</td><td>: <b>Rp {s['nominal']:,}</b></td></tr>
                        <tr><td style="padding: 6px 0; font-weight: bold;">Keperluan/Alasan</td><td>: {s['keperluan']}</td></tr>
                        <tr><td style="padding: 6px 0; font-weight: bold;">Status Berkas</td><td>: <span style="background-color: #d4edda; color: #155724; padding: 2px 8px; border-radius: 4px; font-weight: bold;">VALID & SELESAI (ACC)</span></td></tr>
                    </table>

                    <h4 style="margin-bottom: 10px; border-bottom: 1px solid #ddd; padding-bottom: 5px;">LEMBAR VERIFIKASI TANDA TANGAN DIGITAL</h4>
                    
                    <div style="display: table; width: 100%; text-align: center; font-size: 11px;">
                        <div style="display: table-row;">
                            <div style="display: table-cell; width: 50%; padding-bottom: 15px;">
                                <p style="margin: 0 0 5px 0; font-weight: bold;">1. Pihak Pengaju (Anggota)</p>
                                <img src="data:image/png;base64,{s.get('ttd_pengaju', '')}" style="height: 70px; border: 1px dashed #ccc;" />
                                <p style="margin: 3px 0 0 0; font-style: italic;">({s['nama']})</p>
                            </div>
                            <div style="display: table-cell; width: 50%; padding-bottom: 15px;">
                                <p style="margin: 0 0 5px 0; font-weight: bold;">2. Istri / Keluarga Pengaju</p>
                                {"<img src='data:image/png;base64," + s['ttd_keluarga'] + "' style='height: 70px; border: 1px dashed #ccc;' />" if s.get('ttd_keluarga') else "<p style='color:red;height:70px;line-height:70px;'>[Tanpa TTD]</p>"}
                                <p style="margin: 3px 0 0 0; font-style: italic;">(Penjamin Internal Keluarga)</p>
                            </div>
                        </div>
                        <div style="display: table-row;">
                            <div style="display: table-cell; width: 50%; padding-bottom: 15px;">
                                <p style="margin: 0 0 5px 0; font-weight: bold;">3. Kepala Divisi</p>
                                {"<img src='data:image/png;base64," + s['ttd_kadiv'] + "' style='height: 70px; border: 1px dashed #ccc;' />" if s.get('ttd_kadiv') else "<p style='color:red;height:70px;line-height:70px;'>[Tanpa TTD]</p>"}
                                <p style="margin: 3px 0 0 0; font-style: italic;">(Tim Verifikator I)</p>
                            </div>
                            <div style="display: table-cell; width: 50%; padding-bottom: 15px;">
                                <p style="margin: 0 0 5px 0; font-weight: bold;">4. Kepala Bidang</p>
                                {"<img src='data:image/png;base64," + s['ttd_kabid'] + "' style='height: 70px; border: 1px dashed #ccc;' />" if s.get('ttd_kabid') else "<p style='color:red;height:70px;line-height:70px;'>[Tanpa TTD]</p>"}
                                <p style="margin: 3px 0 0 0; font-style: italic;">(Tim Verifikator II)</p>
                            </div>
                        </div>
                        <div style="display: table-row;">
                            <div style="display: table-cell; width: 50%;"></div>
                            <div style="display: table-cell; width: 50%;">
                                <p style="margin: 0 0 5px 0; font-weight: bold;">5. Direktur Koperasi</p>
                                {"<img src='data:image/png;base64," + s['ttd_direktur'] + "' style='height: 70px; border: 1px dashed #ccc;' />" if s.get('ttd_direktur') else "<p style='color:red;height:70px;line-height:70px;'>[Tanpa TTD]</p>"}
                                <p style="margin: 3px 0 0 0; font-style: italic;">(Pimpinan Tertinggi)</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <script>
                    setTimeout(function() {{
                        var printContents = document.getElementById('print-area').innerHTML;
                        var originalContents = document.body.innerHTML;
                        document.body.innerHTML = printContents;
                        window.print();
                        document.body.innerHTML = originalContents;
                    }}, 1000);
                </script>
                """
                st.components.v1.html(html_template, height=550, scrolling=True)
