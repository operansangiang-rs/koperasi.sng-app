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
                        st.toast(f"💾 Notifikasi: Pengajuan baru atas nama {nama} berhasil disimpan ke server GitHub!", icon="💾")
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
            st.markdown(f"### 📋 Pengajuan: {item['nama']} — Rp {item['nominal']:,}")
            st.write(f"**No Anggota:** {item['no_anggota']}")
            st.write(f"**Keperluan:** {item['keperluan']}")
            st.write("**Silakan Tanda Tangan Kepala Divisi untuk Menyetujui:**")
            
            cv_div = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=150, width=300, key=f"cv_div_{idx}")
            
            if st.button("✍️ Setujui & Kirim Tanda Tangan", key=f"btn_div_{idx}"):
                ttd_div = canvas_to_base64(cv_div.image_data)
                if not ttd_div:
                    st.error("❌ Anda wajib tanda tangan sebelum menyetujui!")
                else:
                    for d in data_saat_ini["database"]:
                        if d["no_anggota"] == item["no_anggota"] and d.get("status", "Menunggu Divisi") == "Menunggu Divisi":
                            d["status"] = "Menunggu Bidang"
                            d["ttd_kadiv"] = ttd_div
                            break
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Setuju Kadiv: {item['nama']}"):
                        st.toast(f"✅ Notifikasi: Persetujuan Kepala Divisi untuk {item['nama']} BERHASIL DISIMPAN!", icon="📝")
                        st.success("✅ Berhasil disetujui! Dialihkan ke Kepala Bidang.")
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
            st.write(f"**No Anggota:** {item['no_anggota']}")
            st.write(f"**Keperluan:** {item['keperluan']}")
            st.write("**Silakan Tanda Tangan Kepala Bidang:**")
            
            cv_bid = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#ffffff", height=150, width=300, key=f"cv_bid_{idx}")
            
            if st.button("✍️ Verifikasi & Tanda Tangan Kabid", key=f"btn_bid_{idx}"):
                ttd_bid = canvas_to_base64(cv_bid.image_data)
                if not ttd_bid:
                    st.error("❌ Anda wajib tanda tangan!")
                else:
                    for d in data_saat_ini["database"]:
                        if d["no_anggota"] == item["no_anggota"] and d.get("status") == "Menunggu Bidang":
                            d["status"] = "Menunggu Direktur"
                            d["ttd_kabid"] = ttd_bid
                            break
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Setuju Kabid: {item['nama']}"):
                        st.toast(f"✅ Notifikasi: Persetujuan Kepala Bidang untuk {item['nama']} BERHASIL DISIMPAN!", icon="💼")
                        st.success("✅ Berhasil disetujui Kabid! Dialihkan ke Direktur.")
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
                    for d in data_saat_ini["database"]:
                        if d["no_anggota"] == item["no_anggota"] and d.get("status") == "Menunggu Direktur":
                            d["status"] = "Menunggu SDM"
                            d["ttd_direktur"] = ttd_dir
                            break
                    if push_database_to_github(data_saat_ini, sha_saat_ini, f"Setuju Direktur: {item['nama']}"):
                        st.toast(f"🏛️ Notifikasi: Persetujuan Direktur untuk {item['nama']} BERHASIL DISIMPAN!", icon="🚀")
                        st.success("✅ Berhasil disetujui Direktur! Dialihkan ke SDM.")
                        st.rerun()
            st.write("---")

    # ---------------------------------------------------------------------
    # ✅ SDM (FINAL ACC & PRINT PDF LENGKAP DENGAN TTD)
    # ---------------------------------------------------------------------
    elif role == "SDM":
        if "print_id" not in st.session_state:
            st.session_state.print_id = None

        items = [i for i in data_saat_ini["database"] if i.get("status") == "Menunggu SDM"]
        if not items: st.info("Tidak ada pengajuan yang siap di-ACC.")
        for idx, item in enumerate(items):
            st.markdown(f"### 📋 Final ACC SDM: {item['nama']} — Rp {item['nominal']:,}")
            st.write(f"**No Anggota:** {item['no_anggota']} | **Keperluan:** {item['keperluan']}")
            
            st.write("**Lembar Tanda Tangan Pengaju (Anggota):**")
            if item.get("ttd_pengaju"):
                st.image(base64.b64decode(item["ttd_pengaju"]), width=200)

            if st.button("🔒 ACC FINAL & NYATAKAN SELESAI", key=f"btn_sdm_{idx}"):
                for d in data_saat_ini["database"]:
                    if d["no_anggota"] == item["no_anggota"] and d.get("status") == "Menunggu SDM":
                        d["status"] = "SELESAI"
                        break
                if push_database_to_github(data_saat_ini, sha_saat_ini, f"Final ACC SDM: {item['nama']}"):
                    st.toast(f"🏁 Notifikasi: Berkas {item['nama']} BERHASIL DISIMPAN & Status SELESAI!", icon="🎉")
                    st.success("Proses Selesai dan disimpan!"); st.rerun()
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
                    st.toast(f"🖨️ Membuka jendela cetak untuk {s['nama']}...", icon="📄")

            # REVISI DI SINI: Jika print_id sesuai, munculkan tombol batal & pratinjau
            if st.session_state.print_id == s['no_anggota']:
                st.write("---")
                # Tombol Batal untuk menutup pratinjau sepenuhnya
                if st.button("❌ Tutup / Batal Cetak", key=f"close_btn_{idx}"):
                    st.session_state.print_id = None
                    st.rerun()
                
                st.info(f"Tekan tombol printer bawaan laptop/HP Anda untuk menyimpannya sebagai **Save as PDF**.")
                
                # Desain Berkas Nota/Formulir HTML Resmi Koperasi Khusus Cetak
                html_template = f"""
                <div id="print-area" style="padding: 25px; border: 2px solid #333; font-family: Arial, sans-serif; background-color: white; color: black; max-width: 700px; margin: auto;">
                    <div style="text-align: center; border-bottom: 3px double #333; padding-bottom: 10px; margin-bottom: 20px;">
                        <h2 style="margin: 0; text-transform: uppercase;">FORMULIR RESMI PINJAMAN KOPERASI</h2>
                        <p style="margin: 5px 0 0 0; font-size: 13px;">Sistem Otomasi Verifikasi Berjenjang Elektronik</p>
                    </div>
                    
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 30px;">
                        <tr><td style="width: 30%; padding: 6px 0; font-weight: bold;">Nama Lengkap</td><td style="width: 70%;">: {s['nama']}</td></tr>
                        <tr><td style="padding: 6px 0; font-weight: bold;">Nomor Anggota</td><td>: {s['no_anggota']}</td></tr>
                        <tr><td style="padding: 6px 0; font-weight: bold;">Nominal Dana</td><td>: <b>Rp {s['nominal']:,}</b></td></tr>
                        <tr><td style="padding: 6px 0; font-weight: bold;">Keperluan/Alasan</td><td>: {s['keperluan']}</td></tr>
                        <tr><td style="padding: 6px 0; font-weight: bold;">Status Berkas</td><td>: <span style="background-color: #d4edda; color: #155724; padding: 2px 8px; border-radius: 4px; font-weight: bold;">VALID & SELESAI (ACC)</span></td></tr>
                    </table>

                    <h4 style="margin-bottom: 15px; border-bottom: 1px solid #ddd; padding-bottom: 5px;">LEMBAR VERIFIKASI TANDA TANGAN DIGITAL</h4>
                    
                    <div style="display: table; width: 100%; text-align: center; font-size: 12px; margin-top: 15px;">
                        <div style="display: table-row;">
                            <div style="display: table-cell; width: 50%; padding-bottom: 20px;">
                                <p style="margin: 0 0 5px 0; font-weight: bold;">1. Pihak Pengaju (Anggota)</p>
                                <img src="data:image/png;base64,{s.get('ttd_pengaju', '')}" style="height: 80px; border: 1px dashed #ccc;" />
                                <p style="margin: 5px 0 0 0; font-style: italic;">({s['nama']})</p>
                            </div>
                            <div style="display: table-cell; width: 50%; padding-bottom: 20px;">
                                <p style="margin: 0 0 5px 0; font-weight: bold;">2. Kepala Divisi</p>
                                {"<img src='data:image/png;base64," + s['ttd_kadiv'] + "' style='height: 80px; border: 1px dashed #ccc;' />" if s.get('ttd_kadiv') else "<p style='color:red;height:80px;line-height:80px;'>[Tanpa TTD]</p>"}
                                <p style="margin: 5px 0 0 0; font-style: italic;">(Tim Verifikator I)</p>
                            </div>
                        </div>
                        <div style="display: table-row;">
                            <div style="display: table-cell; width: 50%;">
                                <p style="margin: 0 0 5px 0; font-weight: bold;">3. Kepala Bidang</p>
                                {"<img src='data:image/png;base64," + s['ttd_kabid'] + "' style='height: 80px; border: 1px dashed #ccc;' />" if s.get('ttd_kabid') else "<p style='color:red;height:80px;line-height:80px;'>[Tanpa TTD]</p>"}
                                <p style="margin: 5px 0 0 0; font-style: italic;">(Tim Verifikator II)</p>
                            </div>
                            <div style="display: table-cell; width: 50%;">
                                <p style="margin: 0 0 5px 0; font-weight: bold;">4. Direktur Koperasi</p>
                                {"<img src='data:image/png;base64," + s['ttd_direktur'] + "' style='height: 80px; border: 1px dashed #ccc;' />" if s.get('ttd_direktur') else "<p style='color:red;height:80px;line-height:80px;'>[Tanpa TTD]</p>"}
                                <p style="margin: 5px 0 0 0; font-style: italic;">(Pimpinan Tertinggi)</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <script>
                    // Otomatis mentrigger fungsi print jendela browser agar bisa save PDF langsung
                    setTimeout(function() {{
                        var printContents = document.getElementById('print-area').innerHTML;
                        var originalContents = document.body.innerHTML;
                        document.body.innerHTML = printContents;
                        window.print();
                        document.body.innerHTML = originalContents;
                    }}, 1000);
                </script>
                """
                # Tampilkan Preview Dokumen Resmi di Web Streamlit sebelum terdownload
                st.components.v1.html(html_template, height=550, scrolling=True)
