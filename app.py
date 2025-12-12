import streamlit as st
from PIL import Image
import google.generativeai as genai
import datetime
import time
import io
import json
import os
import requests
import base64
from urllib.parse import quote

# ==========================================
# 📦 KÜTÜPHANE KONTROLLERİ
# ==========================================
try:
    from streamlit_paste_button import paste_image_button
    PASTE_ENABLED = True
except ImportError:
    PASTE_ENABLED = False

try:
    import feedparser
    NEWS_ENABLED = True
except ImportError:
    NEWS_ENABLED = False

# Firebase Kontrolü
try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_ENABLED = True
except ImportError:
    FIREBASE_ENABLED = False

# ==========================================
# 🔐 AYARLAR VE FIREBASE BAĞLANTISI
# ==========================================
CONFIG_FILE = "site_config.json"
FIREBASE_DB_URL = 'https://borsakopru-default-rtdb.firebaseio.com/' 

def init_firebase():
    """Firebase bağlantısını başlatır (Singleton)"""
    if not FIREBASE_ENABLED: return False
    try:
        if not firebase_admin._apps:
            if "firebase" in st.secrets:
                key_dict = json.loads(st.secrets["firebase"]["json_content"])
                cred = credentials.Certificate(key_dict)
            elif os.path.exists("firebase_key.json"):
                cred = credentials.Certificate("firebase_key.json")
            else:
                return False
            firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})
        return True
    except Exception as e:
        st.error(f"Firebase Hatası: {e}")
        return False

firebase_ready = init_firebase()

def load_global_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: return json.load(f)
        except: return {"beta_active": True}
    return {"beta_active": True}

def save_global_config(config):
    with open(CONFIG_FILE, "w") as f: json.dump(config, f)

global_config = load_global_config()


# ==========================================
# 🎯 MERKEZİ FONKSİYON TANIMLARI
# ==========================================

def get_model(key):
    """API key ile kullanılabilecek modeli bulur"""
    try:
        genai.configure(api_key=key)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in models:
            if "gemini-2.5-flash" in m: return m
        return models[0] if models else None
    except: return None

# --- GÖRSEL KALİTESİ KORUMA (RAW MOD - ASLA SIKIŞTIRMA YOK) ---
def compress_image(image):
    """Görseli ASLA küçültmez. Piksel kaybını önler."""
    if image.mode in ("RGBA", "P"): 
        image = image.convert("RGB")
    return image

def fetch_stock_news(symbol):
    """Google News RSS (Son 24 Saat)"""
    if not NEWS_ENABLED: return "Haber modülü aktif değil."
    try:
        query = f"{symbol} Borsa KAP when:1d"
        rss_url = f"https://news.google.com/rss/search?q={quote(query)}&hl=tr&gl=TR&ceid=TR:tr"
        feed = feedparser.parse(rss_url)
        news_list = []
        for entry in feed.entries[:5]: 
            published = entry.published_parsed
            date_str = time.strftime("%d.%m.%Y %H:%M", published) if published else "Tarih Yok"
            news_list.append(f"- {entry.title} ({date_str})")
        if not news_list: return "Son 24 saatte önemli haber yok."
        return "\n".join(news_list)
    except Exception as e:
        return f"Haber çekme hatası: {str(e)}"

def fetch_data_via_bridge(symbol, data_type):
    """Firebase üzerinden PC'deki bridge.py ile konuşur"""
    if not firebase_ready:
        st.error("Veritabanı bağlantısı yok.")
        return None

    status_area = st.empty()
    try:
        status_area.info(f"📡 {symbol} için {data_type} isteniyor... PC'ye bağlanılıyor.")
        ref_req = db.reference('bridge/request')
        ref_req.set({
            'symbol': symbol,
            'type': data_type,
            'status': 'pending',
            'timestamp': time.time()
        })
        
        progress_bar = st.progress(0)
        for i in range(25):
            time.sleep(1)
            progress_bar.progress((i + 1) / 25)
            status_data = ref_req.get()
            status = status_data.get('status') if status_data else None
            
            if status == 'processing':
                status_area.warning("⏳ Robot emri aldı, Telegram'dan yanıt bekleniyor...")
            elif status == 'completed':
                status_area.success("✅ Veri Alındı!")
                progress_bar.empty()
                ref_res = db.reference('bridge/response')
                data = ref_res.get()
                if data and 'image_base64' in data:
                    img_bytes = base64.b64decode(data['image_base64'])
                    return Image.open(io.BytesIO(img_bytes))
                break
            elif status == 'timeout':
                status_area.error("❌ Zaman aşımı. Hedef bot cevap vermedi.")
                break
        else:
            status_area.error("❌ Yanıt yok. PC'deki 'bridge.py' çalışıyor mu?")
    except Exception as e:
        status_area.error(f"Hata: {e}")
    return None

# ==========================================
# 🎨 SAYFA AYARLARI VE CERRAH TİTİZLİĞİNDE CSS
# ==========================================

st.set_page_config(page_title="BIST Yapay Zeka PRO", layout="wide", page_icon="🐋")

st.markdown("""
<style>
    /* --- SIDEBAR'I KURTARAN, GEREKSİZLERİ SİLEN CSS --- */
    
    /* 1. Header'ı YOK ETME, Sadece Şeffaf Yap (Böylece Sol Üstteki Ok Kalır) */
    header[data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
        z-index: 1 !important; /* Sidebar butonunun tıklanabilir kalması için */
    }

    /* 2. Sadece SAĞ TARAFTAKİ Menüyü (Toolbar) Gizle */
    [data-testid="stToolbar"] {
        display: none !important;
    }

    /* 3. Üstteki Renkli Çizgiyi (Decoration) Gizle */
    [data-testid="stDecoration"] {
        display: none !important;
    }

    /* 4. Footer ve Sağ Alt Köşeyi Tamamen Yok Et */
    footer {
        display: none !important;
    }
    .stAppDeployButton, [data-testid="stAppDeployButton"] {
        display: none !important;
    }
    [data-testid="stStatusWidget"] {
        display: none !important;
    }

    /* --- DİĞER ARAYÜZ --- */
    .st-emotion-cache-n1sltv p { font-size: 10px; }
    .main { background-color: #0e1117; }
    h1 { color: #00d4ff !important; }
    h2 { color: #ffbd45 !important; border-bottom: 2px solid #ffbd45; padding-bottom: 10px;}
    .stAlert { border-left: 5px solid #ffbd45; }
    
    .x-btn, .live-data-btn {
        display: inline-block; padding: 12px 20px; text-align: center; text-decoration: none;
        font-size: 16px; border-radius: 8px; width: 100%; margin-top: 10px; font-weight: bold;
        transition: 0.3s; color: white !important;
    }
    .x-btn { background-color: #000000; border: 1px solid #333; }
    .x-btn:hover { background-color: #1a1a1a; border-color: #1d9bf0; }
    
    .live-data-btn { background-color: #d90429; border: 1px solid #ef233c; }
    .live-data-btn:hover { background-color: #ef233c; }

    .key-status-pass { color: #00ff00; font-weight: bold; font-size: x-small; }
    .key-status-fail { color: #ff4444; font-weight: bold; font-size: x-small; }
    .key-status-limit { color: #ffbd45; font-weight: bold; font-size: x-small; }

    div.stButton > button[kind="secondary"]:first-child {
        padding: 0 4px; font-size: 8px; min-height: 20px; line-height: 0; margin-top: -10px;
    }
    .element-container:has(> .stJson) { display: none; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# --- SESSION INIT ---
# ==========================================
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "is_admin" not in st.session_state: st.session_state.is_admin = False
if "reset_counter" not in st.session_state: st.session_state.reset_counter = 0
if "analysis_result" not in st.session_state: st.session_state.analysis_result = None
if "messages" not in st.session_state: st.session_state.messages = []
if "loaded_count" not in st.session_state: st.session_state.loaded_count = 0
if "active_working_key" not in st.session_state: st.session_state.active_working_key = None
if "key_status" not in st.session_state: st.session_state.key_status = {}

if "api_depth_data" not in st.session_state: st.session_state.api_depth_data = None
if "api_akd_data" not in st.session_state: st.session_state.api_akd_data = None
if "tg_img_derinlik" not in st.session_state: st.session_state.tg_img_derinlik = None
if "tg_img_akd" not in st.session_state: st.session_state.tg_img_akd = None
if "tg_img_kademe" not in st.session_state: st.session_state.tg_img_kademe = None
if "tg_img_takas" not in st.session_state: st.session_state.tg_img_takas = None

# API KEY INIT
if "api_keys" not in st.session_state:
    api_keys_raw = st.secrets.get("GOOGLE_API_KEY", "")
    st.session_state.api_keys = [k.strip() for k in api_keys_raw.split(",") if k.strip()]

for cat in ["Derinlik", "AKD", "Kademe", "Takas"]:
    if f"pasted_{cat}" not in st.session_state: 
        st.session_state[f"pasted_{cat}"] = []

api_keys = st.session_state.api_keys 

# --- AUTH LOGIC ---
query_params = st.query_params
admin_secret = st.secrets.get("ADMIN_KEY", "admin123") 

if query_params.get("admin") == admin_secret:
    st.session_state.authenticated = True
    st.session_state.is_admin = True

def check_password():
    if "APP_PASSWORD" in st.secrets:
        correct_password = st.secrets["APP_PASSWORD"]
    else:
        st.error("🚨 Secrets Hatası.")
        st.stop()

    input_pass = st.session_state.get("password_input", "")
    if input_pass == admin_secret:
        st.session_state.authenticated = True
        st.session_state.is_admin = True
        return
    if input_pass == correct_password:
        if global_config["beta_active"]:
            st.session_state.authenticated = True
            st.session_state.is_admin = False
        else:
            st.error("🔒 Beta kapalı.")
    elif input_pass:
        st.error("❌ Hatalı Kod!")

# --- LOGIN SCREEN ---
if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='border: 2px solid #00d4ff; padding: 40px; border-radius: 15px; background-color: #1E2130; text-align: center; margin-top: 50px;'>", unsafe_allow_html=True)
        st.title("🔒 Beta Erişim")
        if global_config["beta_active"]:
            st.text_input("Giriş Kodu:", type="password", key="password_input", on_change=check_password)
            if st.button("Giriş Yap"): check_password()
        else:
            st.warning("⚠️ BAKIMDA")
            with st.expander("Yönetici"):
                st.text_input("Admin:", type="password", key="password_input", on_change=check_password)
                if st.button("Yönetici Gir"): check_password()
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop() 

# ==========================================
# 🚀 MAIN APP
# ==========================================

col_title, col_reset = st.columns([5, 1])
with col_title:
    st.title("🐋 BIST Yapay Zeka PRO")
    if st.session_state.is_admin: st.success("👑 YÖNETİCİ MODU")
    else: st.info("Küçük Yatırımcının Büyüdüğü Bir Evren..")

with col_reset:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 SİSTEMİ SIFIRLA", type="secondary"):
        st.session_state.reset_counter += 1
        st.session_state.api_depth_data = None
        st.session_state.api_akd_data = None
        st.session_state.tg_img_derinlik = None
        st.session_state.tg_img_akd = None
        st.session_state.tg_img_kademe = None
        st.session_state.tg_img_takas = None
        
        keys_to_keep = ["authenticated", "is_admin", "reset_counter", "api_depth_data", "api_akd_data", "tg_img_derinlik", "tg_img_akd", "tg_img_kademe", "tg_img_takas", "key_status", "api_keys"]
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep: del st.session_state[key]
        for cat in ["Derinlik", "AKD", "Kademe", "Takas"]:
            st.session_state[f"pasted_{cat}"] = []
        st.rerun()

# --- API & DATA FETCH SECTION ---
st.markdown("---")
st.subheader("📡 Veri Merkezi")

api_col1, api_col2 = st.columns([3, 1])
with api_col1:
    api_ticker_input = st.text_input("Hisse Kodu:", "THYAO", key="api_ticker").upper()
with api_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    fetch_btn = st.button("Derinlik - AKD Verilerini AL", type="primary")

if fetch_btn:
    try:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        headers = {'User-Agent': 'Mozilla/5.0'}
        with st.spinner(f"{api_ticker_input} Verileri Çekiliyor..."):
            url_depth = f"https://webapi.hisseplus.com/api/v1/derinlik?sembol={api_ticker_input}"
            r_depth = requests.get(url_depth, headers=headers)
            st.session_state.api_depth_data = r_depth.json() if r_depth.status_code == 200 else None
            url_akd = f"https://webapi.hisseplus.com/api/v1/akd?sembol={api_ticker_input}&ilk={today_str}&son={today_str}"
            r_akd = requests.get(url_akd, headers=headers)
            st.session_state.api_akd_data = r_akd.json() if r_akd.status_code == 200 else None
    except Exception as e:
        st.error(f"API Hatası: {e}")

# --- DATA STATUS ---
if st.session_state.api_depth_data or st.session_state.api_akd_data:
    st.markdown("##### 📊 Veri Durumu")
    stat_col1, stat_col2 = st.columns(2)
    with stat_col1:
        if st.session_state.api_depth_data: st.success("API DERİNLİK 🟢")
        else: st.error("API DERİNLİK 🔴")
    with stat_col2:
        if st.session_state.api_akd_data: st.success("API AKD 🟢")
        else: st.error("API AKD 🔴")

valid_model_name = None
working_key = None
for k in api_keys:
    mod = get_model(k)
    if mod: 
        valid_model_name = mod
        working_key = k 
        break

if not valid_model_name:
    st.error("❌ Aktif Model Bulunamadı. Lütfen API anahtarlarınızı kontrol edin.")
    if not st.session_state.is_admin: st.stop()

# --- UPLOAD SECTION ---
file_key_suffix = str(st.session_state.reset_counter)

def handle_paste(cat):
    if PASTE_ENABLED:
        res = paste_image_button(
            label=f"📋 Yapıştır", 
            background_color="#1E2130", hover_background_color="#333",
            key=f"paste_{cat}_{file_key_suffix}"
        )
        if res.image_data is not None:
            if not st.session_state[f"pasted_{cat}"] or st.session_state[f"pasted_{cat}"][-1] != res.image_data:
                st.session_state[f"pasted_{cat}"].append(res.image_data)

def show_images(cat):
    if st.session_state[f"pasted_{cat}"]:
        st.markdown(f"**📋 Pano ({len(st.session_state[f'pasted_{cat}'])}):**")
        cols = st.columns(3)
        for i, img in enumerate(st.session_state[f"pasted_{cat}"]):
            with cols[i % 3]:
                st.image(img, use_container_width=True)
                if st.button("🗑️ Sil", key=f"del_{cat}_{i}_{st.session_state.reset_counter}"):
                    st.session_state[f"pasted_{cat}"].pop(i) 
                    st.rerun() 
        if st.button(f"🗑️ Tüm {cat} Görsellerini Temizle", key=f"clear_all_{cat}"):
            st.session_state[f"pasted_{cat}"] = []
            st.rerun()

def render_category_panel(title, cat_name, tg_session_key, uploader_key):
    st.markdown(f"### {title}")
    if st.session_state[tg_session_key]:
        with st.container(border=True):
            st.caption("📲 Telegram'dan Alındı")
            st.image(st.session_state[tg_session_key], width=100, caption="TG Verisi") 
            if st.button("🗑️ Kaldır", key=f"del_tg_{cat_name}"):
                st.session_state[tg_session_key] = None
                st.rerun()
    uploaded_files = st.file_uploader("Dosya Yükle", type=["jpg","png","jpeg"], key=uploader_key, accept_multiple_files=True)
    handle_paste(cat_name) 
    show_images(cat_name)  
    return uploaded_files

col1, col2 = st.columns(2)
with col1:
    img_d = render_category_panel("1. Derinlik 💹", "Derinlik", "tg_img_derinlik", f"d_{file_key_suffix}")
    st.markdown("---") 
    img_k = render_category_panel("3. Kademe 📊", "Kademe", "tg_img_kademe", f"k_{file_key_suffix}")
with col2:
    img_a = render_category_panel("2. AKD 🤵", "AKD", "tg_img_akd", f"a_{file_key_suffix}")
    st.markdown("---") 
    img_t = render_category_panel("4. Takas 🌍", "Takas", "tg_img_takas", f"t_{file_key_suffix}")

# --- SIDEBAR ---
def add_api_key():
    new_key = st.session_state.new_api_key_input.strip()
    if new_key and new_key not in st.session_state.api_keys:
        st.session_state.api_keys.append(new_key)
        st.session_state.new_api_key_input = ""
        st.rerun()

def delete_api_key(key_to_delete):
    if key_to_delete in st.session_state.api_keys:
        st.session_state.api_keys.remove(key_to_delete)
        if key_to_delete in st.session_state.key_status:
            del st.session_state.key_status[key_to_delete]
        st.rerun()

with st.sidebar:
    if st.session_state.is_admin:
        st.subheader("⚙️ Yönetici Kontrol Paneli")
        curr = global_config["beta_active"]
        new_s = st.toggle("Beta Açık", value=curr)
        if new_s != curr:
            global_config["beta_active"] = new_s
            save_global_config(global_config)
            st.rerun()

        with st.expander("🔑 API Anahtar Havuzu Yönetimi", expanded=True):
            st.markdown(f"<span style='font-size: small;'>Aktif Key Sayısı: {len(api_keys)}</span>", unsafe_allow_html=True)
            st.text_input("Yeni Key Ekle:", type="password", key="new_api_key_input")
            if st.button("➕ Anahtarı Ekle", on_click=add_api_key, use_container_width=True): pass
            st.markdown("---")
            for k in api_keys:
                cols = st.columns([1, 3, 2])
                key_display = f"<span style='font-size: x-small; font-weight: bold;'>...{k[-4:]}</span>"
                if k in st.session_state.key_status:
                    s = st.session_state.key_status[k]
                    lite_status = s.get('lite', '❓')
                    flash_status = s.get('flash', '❓')
                    status_text = f"<span style='font-size: xx-small;'>Lite: {lite_status} | Flash: {flash_status}</span>"
                else:
                    status_text = "<span style='font-size: x-small;' class='key-status-limit'>❓ TEST ET</span>"
                with cols[0]:
                    if st.button("❌", key=f"del_key_{k[-4:]}_v4", on_click=delete_api_key, args=(k,)): pass
                with cols[1]: st.markdown(key_display, unsafe_allow_html=True)
                with cols[2]: st.markdown(status_text, unsafe_allow_html=True)
            st.markdown("---")
            if st.button("🔄 Kota Testi", use_container_width=True, key="admin_key_test"):
                st.session_state.key_status = {}
                prog = st.progress(0)
                test_prompt = "Hello" 
                def test_model_quota(api_key, model_name):
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel(model_name)
                        model.generate_content(test_prompt)
                        return "✅ OK"
                    except Exception as e:
                        error_str = str(e).lower()
                        if "429" in error_str or "quota" in error_str: return "<span class='key-status-limit'>⚠️ KOTA</span>"
                        elif "model" in error_str: return "<span class='key-status-fail'>❌ MODEL YOK</span>"
                        else: return "<span class='key-status-fail'>❌ HATA</span>"
                for i, k in enumerate(api_keys):
                    key_results = {}
                    key_results['lite'] = test_model_quota(k, 'gemini-2.5-flash-lite')
                    key_results['flash'] = test_model_quota(k, 'gemini-2.5-flash')
                    st.session_state.key_status[k] = key_results
                    prog.progress((i+1)/len(api_keys))
                    time.sleep(0.5)
                prog.empty()
                st.rerun()
        st.markdown("---")

    st.header("📲 Telegram Köprüsü")
    tg_ticker = st.text_input("Hisse Kodu (TG):", api_ticker_input, key="tg_ticker_final").upper() 
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        if st.button("📉 Derinlik", key="tg_dr"): st.session_state.tg_img_derinlik = fetch_data_via_bridge(tg_ticker, "derinlik")
    with col_t2:
        if st.button("🏦 AKD", key="tg_akd"): st.session_state.tg_img_akd = fetch_data_via_bridge(tg_ticker, "akd")
    col_t3, col_t4 = st.columns(2)
    with col_t3:
        if st.button("📊 Kademe", key="tg_kdm"): st.session_state.tg_img_kademe = fetch_data_via_bridge(tg_ticker, "kademe")
    with col_t4:
        if st.button("🌍 Takas", key="tg_tks"): st.session_state.tg_img_takas = fetch_data_via_bridge(tg_ticker, "takas")

    st.markdown("---")
    if st.button("🚪 Çıkış Yap", key="logout_btn"):
        st.session_state.authenticated = False
        st.rerun()

    st.markdown("---")
    st.header("𝕏 Tarayıcı")
    raw_ticker = st.text_input("Kod:", api_ticker_input, key="x_ticker_input").upper()
    clean_ticker = raw_ticker.replace("#", "").strip()
    search_mode = st.radio("Tip:", ("🔥 Geçmiş", "⏱️ Canlı"), key="x_search_mode")
    if search_mode == "🔥 Geçmiş":
        s_date = st.date_input("Tarih", datetime.date.today(), key="x_date_input")
        url = f"https://x.com/search?q={quote(f'#{clean_ticker} lang:tr until:{s_date + datetime.timedelta(days=1)} since:{s_date} min_faves:5')}&src=typed_query&f=top"
        btn_txt = f"🔥 <b>{s_date}</b> Popüler"
    else:
        url = f"https://x.com/search?q={quote(f'#{clean_ticker} lang:tr')}&src=typed_query&f=live"
        btn_txt = f"⏱️ Son Dakika"
    st.markdown(f"""<a href="{url}" target="_blank" class="x-btn">{btn_txt}</a>""", unsafe_allow_html=True)

# --- ANALYZE ---
st.markdown("---")
c1, c2 = st.columns([1, 1])
MODEL_OPTIONS = {"gemini-2.5-flash": "🚀 Flash", "gemini-2.5-flash-lite": "⚡ Lite"}

with c2:
    st.markdown("##### 🛠️ Analiz Ayarları")
    use_lite_model = st.checkbox("⚡ Lite Modeli Kullan (Daha Hızlı)", key="use_lite_model_checkbox", value=False)
    analysis_mode = st.radio(
        "Analiz Modu Seçiniz:",
        options=["⚡ SADE MOD (Öz ve Net)", "🛡️ DESTEK-DİRENÇ MODU (Özel Strateji)", "🧠 GELİŞMİŞ MOD (Ultra Detay - 50 Madde)"],
        index=0
    )
    if "GELİŞMİŞ" in analysis_mode:
        max_items = st.slider("Gelişmiş Mod Madde Sayısı", 10, 50, 20)

with c1:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🐋 ANALİZİ BAŞLAT", type="primary", use_container_width=True):
        if not api_keys:
            st.error("❌ API Anahtar Havuzu Boş!")
            st.stop()
            
        input_data = []
        context_str = ""
        if st.session_state.api_depth_data:
            context_str += f"\n\n--- CANLI DERİNLİK API VERİSİ ---\n{json.dumps(st.session_state.api_depth_data, indent=2, ensure_ascii=False)}"
        if st.session_state.api_akd_data:
            context_str += f"\n\n--- CANLI AKD API VERİSİ ---\n{json.dumps(st.session_state.api_akd_data, indent=2, ensure_ascii=False)}"

        if NEWS_ENABLED:
            with st.spinner("Haberler taranıyor..."):
                news_text = fetch_stock_news(api_ticker_input)
                context_str += f"\n\n--- HABERLER ({api_ticker_input}) ---\n{news_text}"

        def add_imgs(fl, pl, tg_img):
            added = False
            if fl: [input_data.append(compress_image(Image.open(f))) for f in fl]; added=True
            if pl: [input_data.append(compress_image(i)) for i in pl]; added=True
            if tg_img: input_data.append(compress_image(tg_img)); added=True
            return added

        has_d = add_imgs(img_d, st.session_state["pasted_Derinlik"], st.session_state.tg_img_derinlik)
        has_a = add_imgs(img_a, st.session_state["pasted_AKD"], st.session_state.tg_img_akd)
        has_k = add_imgs(img_k, st.session_state["pasted_Kademe"], st.session_state.tg_img_kademe)
        has_t = add_imgs(img_t, st.session_state["pasted_Takas"], st.session_state.tg_img_takas)
        
        is_depth_avail = has_d or st.session_state.api_depth_data
        is_akd_avail = has_a or st.session_state.api_akd_data
        is_kademe_avail = has_k
        is_takas_avail = has_t
        
        base_role = f"""
        Sen Borsa Uzmanısın ve Kıdemli Veri Analistisin.
        GÖREV: SADECE sana sağlanan görselleri ve verileri kullanarak analiz yap.
        🚨 Hisse kodunu görselden veya veriden tespit et.
        --- MEVCUT VERİ SETİ ---
        {context_str}
        --- ⚠️ KRİTİK KURALLAR ---
        1. 🚫 **YASAK:** Elimizde verisi olmayan başlıkları rapora ekleme.
        2. 🚫 **YASAK:** Giriş cümlesi yazma. Direkt analize başla.
        3. 🎨 **RENK:** :green[**OLUMLU**], :blue[**NÖTR**], :red[**OLUMSUZ**] cümlelerin yanına ekle.
        4. 🚫 **YASAK:** Listeyi doldurmak için aynı satırı tekrarlama. Sadece gördüğün kadarını yaz.
        5. ⚠️ **DİKKAT:** Tablodaki "Fiyat" (TL) ve "Lot/Adet" (Volume) sütunlarını karıştırma. Genellikle "Lot" sütunu daha büyük tam sayılar içerir.
        6. 🧠 **MANTIK VE FİYAT KONTROLÜ (ÇOK ÖNEMLİ):**
           - Önce görseldeki **ANLIK FİYATI** (Current Price) tespit et.
           - **KURAL 1:** Anlık fiyattan **YÜKSEK** olan emirler **SATIŞ (DİRENÇ)** emirleridir. (Asla bunlara 'Alış' deme!)
           - **KURAL 2:** Anlık fiyattan **DÜŞÜK** olan emirler **ALIŞ (DESTEK)** emirleridir.
           - ÖRNEK: Fiyat 22.58 ise, 22.90'daki yığılma **SATIŞ (DİRENÇ)** olur. 22.10'daki yığılma **ALIŞ (DESTEK)** olur. Bunu karıştırma!
        """
        
        destek_direnc_prompt_sade = """
        ## 🛡️ GÜÇLÜ/ZAYIF DESTEK VE DİRENÇ ANALİZİ
        (GÖREV: SADECE VERİDE GÖRDÜĞÜN, "BALİNA GİRİŞİ" OLAN ÖNEMLİ SEVİYELERİ YAZ.)
        (DİKKAT: 15 adet yazmak zorunda DEĞİLSİN. Eğer sadece 3 tane varsa, 3 tane yaz.)
        (EĞER bir seviyede AŞIRI YÜKSEK LOT (Balina) varsa yanına "🔥 :green[**ÇOK GÜÇLÜ ALIM**]" veya "🔥 :red[**ÇOK GÜÇLÜ SATIM**]" yaz. Yoksa sadece fiyatı bırak.)
        (Hatırlatma: Güncel fiyattan YÜKSEK olanlar SATIŞ/DİRENÇ, DÜŞÜK olanlar ALIŞ/DESTEK'tir.)
        (FORMAT: **[FİYAT]**: [NEDENİ - Lot miktarı vs.] [VARSA GÜÇ İBARESİ])
        """
        
        guc_siralama_prompt = """
        ## 🏅 GÜÇ VE ÖNEM SIRALAMASI
        (Bulduğun seviyeleri, ÖNEM sırasına göre diz. En çok lot olandan en aza doğru.)
        (Sadece tespit edebildiğin kadarını yaz, listeyi zorlama.)
        * **DESTEKLER (Güçlüden Zayıfa):** [Fiyat] ...
        * **DİRENÇLER (Güçlüden Zayıfa):** [Fiyat] ...
        """

        if "SADE" in analysis_mode:
            req_sections = ""
            if is_depth_avail: req_sections += """\n## 💹 DERİNLİK ANALİZİ (EN AZ 5 MADDE)\n"""
            if is_akd_avail: req_sections += """\n## 🤵 AKD ANALİZİ (EN AZ 5 MADDE)\n"""
            if is_kademe_avail: req_sections += """\n## 📊 KADEME ANALİZİ (EN AZ 5 MADDE)\n"""
            if is_takas_avail: req_sections += """\n## 🌍 TAKAS ANALİZİ (EN AZ 5 MADDE)\n"""

            prompt = base_role + f"""
            --- ⚡ SADE MOD ---
            {req_sections}
            {destek_direnc_prompt_sade}
            ## 🐋 GENEL SENTEZ
            ## 7. 🧭 YÖN / FİYAT OLASILIĞI
            ## 8. 💯 SKOR KARTI
            ## 9. 🚀 İŞLEM PLANI
            """
        elif "DESTEK" in analysis_mode:
            prompt = base_role + f"""
            --- 🛡️ DESTEK-DİRENÇ VE SEVİYE ANALİZİ MODU ---
            GÖREV: Bu modda SADECE kritik fiyat seviyelerine odaklan.
            
            ## 🧱 KRİTİK DESTEK BÖLGELERİ (Mevcut Olanlar)
            (Hatırlatma: Güncel fiyattan DÜŞÜK olanlar DESTEKTİR.)
            1. **[FİYAT]**: [NEDENİ]
            ... (Sadece olan kadar yaz)

            ## 🚧 KRİTİK DİRENÇ BÖLGELERİ (Mevcut Olanlar)
            (Hatırlatma: Güncel fiyattan YÜKSEK olanlar DİRENÇTİR.)
            1. **[FİYAT]**: [NEDENİ]
            ... (Sadece olan kadar yaz)

            {guc_siralama_prompt}
            
            ## ⚖️ KİLİT RAKAM (PİVOT)
            ## 📉 GAP (BOŞLUK) ANALİZİ
            ## 🚀 ALIM-SATIM STRATEJİSİ
            """
        else:
            limit_txt = f"(DİKKAT: SADECE VERİDE OLANLARI YAZ, UYDURMA.)"
            main_headers = ""
            if is_depth_avail: main_headers += f"## 📸 DERİNLİK ANALİZİ {limit_txt}\n"
            if is_akd_avail: main_headers += f"## 🏦 AKD ANALİZİ {limit_txt}\n"
            if is_kademe_avail: main_headers += f"## 📊 KADEME ANALİZİ {limit_txt}\n"
            if is_takas_avail: main_headers += f"## 🌍 TAKAS ANALİZİ {limit_txt}\n"

            prompt = base_role + f"""
            --- 🧠 GELİŞMİŞ MOD ---
            {main_headers}
            {destek_direnc_prompt_sade}
            --- 🕵️‍♂️ MİKRO-YAPISAL ANALİZ (50 MADDE KONTROLÜ) ---
            (Mevcut listeden sadece cevabı olanları yaz)
            --- FİNAL ---
            ## 🐋 GENEL SENTEZ
            ## 🧭 YÖN / FİYAT OLASILIĞI
            ## 💯 SKOR KARTI
            ## 🚀 İŞLEM PLANI
            """

        input_data.append(prompt)
        
        count = 0
        if has_d: count += 1
        if has_a: count += 1
        if has_k: count += 1
        if has_t: count += 1
        
        if count == 0 and not context_str:
            st.warning("⚠️ Lütfen analiz için veri yükleyin.")
        else:
            if st.session_state.get("use_lite_model_checkbox"):
                primary_model = "gemini-2.5-flash-lite"
                model_priority = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
            else:
                primary_model = "gemini-2.5-flash"
                model_priority = ["gemini-2.5-flash", "gemini-2.5-flash-lite"] 
            
            placeholder = st.empty()
            full_response = ""
            
            with st.spinner(f"Analiz ({MODEL_OPTIONS.get(primary_model, primary_model)}) ile Başlatılıyor..."):
                stream_active = False
                local_keys = api_keys.copy()
                if working_key and working_key in local_keys:
                    local_keys.remove(working_key)
                    local_keys.insert(0, working_key)
                    
                for k in local_keys:
                    for model_name in model_priority:
                        try:
                            genai.configure(api_key=k)
                            model = genai.GenerativeModel(model_name)
                            stream = model.generate_content(input_data, stream=True)
                            st.session_state.active_working_key = k
                            working_key = k
                            stream_active = True
                            
                            for chunk in stream:
                                if chunk.text:
                                    full_response += chunk.text
                                    placeholder.markdown(full_response + "▌") 
                            
                            placeholder.markdown(full_response)
                            st.session_state.analysis_result = full_response
                            st.session_state.loaded_count = count
                            time.sleep(1)
                            break 
                        except Exception as e:
                            error_str = str(e).lower()
                            if "429" in error_str or "quota" in error_str: 
                                if model_name == model_priority[-1]: st.warning(f"⚠️ Anahtar `...{k[-4:]}` dolu.")
                                continue
                            elif "expired" in error_str or "invalid" in error_str:
                                if model_name == model_priority[-1]: st.warning(f"⚠️ Anahtar `...{k[-4:]}` geçersiz.")
                                continue
                            else: 
                                st.error(f"Hata: {e}"); break
                    if stream_active: break
                if not stream_active: st.error("Tüm kotalar dolu.")

if st.session_state.analysis_result:
    st.markdown("## 🐋 Kurumsal Rapor")
    st.markdown(st.session_state.analysis_result)
    st.markdown("---")
    st.subheader("💬 Analist ile Sohbet")
    
    col_c1, col_c2 = st.columns([1, 4])
    with col_c1:
        st.markdown("**Mod:**")
        chat_scope = st.radio("M", ("📝 RAPOR", "🌍 GENEL"), label_visibility="collapsed")

    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if q := st.chat_input("Soru sor..."):
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)

        with st.chat_message("assistant"):
            local_keys = api_keys.copy()
            if st.session_state.active_working_key and st.session_state.active_working_key in local_keys:
                local_keys.remove(st.session_state.active_working_key)
                local_keys.insert(0, st.session_state.active_working_key)
            
            key_found = False
            full_resp = ""
            for k in local_keys:
                try:
                    sys_inst = ("GÖREV: Sadece rapora sadık kal." if chat_scope == "📝 RAPOR" else "GÖREV: Raporu temel al ama genel borsa bilginle yorum kat.")
                    final_prompt = f"{sys_inst}\n\nRAPOR:\n{st.session_state.analysis_result}\n\nSORU:\n{q}"
                    genai.configure(api_key=k)
                    model = genai.GenerativeModel(valid_model_name)
                    stream = model.generate_content(final_prompt, stream=True)
                    st.session_state.active_working_key = k 
                    key_found = True
                    def parser():
                        for ch in stream:
                            if ch.text: yield ch.text
                    resp = st.write_stream(parser)
                    full_resp = resp
                    time.sleep(1)
                    break 
                except Exception as e:
                    error_str = str(e).lower()
                    if "429" in error_str or "quota" in error_str: continue 
                    else: break 
            
            if key_found: st.session_state.messages.append({"role": "assistant", "content": full_resp})
            else: st.error("❌ Sohbet Hatası")
