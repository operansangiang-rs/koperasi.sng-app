import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import json
import base64
import io
import requests

st.set_page_config(page_title="Sistem Pengajuan & Approval Koperasi", layout="centered")

# =========================================================================
# 🔐 MENGAMBIL DATA REPO & TOKEN AMAN DARI STREAMLIT SECRETS
# =========================================================================
try:
    GITHUB_TOKEN = st.secrets["github"]["token"]
    REPO_NAME = st.secrets["github"]["repo"]
except Exception:
    GITHUB_TOKEN = ""
    REPO_NAME = ""

DB_FILE = "data_store.json"

TEMPLATE_AWAL = {
    "database": [],
    "categories": ["Pinjaman Rutin", "Pinjaman Darurat", "Pinjaman Modal Usaha"]
}

# Fungsi Membaca Data dari GitHub
def load_data_from_github():
    if GITHUB_TOKEN.startswith("ghp_") and "/" in REPO_NAME:
        url = f"https://api.github.com/repos/{REPO_NAME}/contents/{DB_FILE}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            file_content = response.json()
            content_decoded =
