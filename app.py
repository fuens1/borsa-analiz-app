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
# 🎨 SAYFA AYARLARI
# ==========================================

st.set_page_config(page_title="BIST Yapay Zeka PRO", layout="wide", page_icon="🐋")

# 👇👇👇 GÜNCELLENMİŞ "ATOM BOMBASI" GİZLEME KODU 👇👇👇
st.markdown("""
<style>
    /* 1. Üstteki Renkli Şerit ve Menü (Header) */
    [data-testid="stHeader"] { display: none; }
    
    /* 2. Sayfanın En Altındaki Standart Footer */
    [data-testid="stFooter"] { display: none; }
    footer { visibility: hidden; }

    /* 3. SAĞ ALTTAKİ 'DEPLOY' BUTONU (Kırmızı Taç/Logo) */
    .stAppDeployButton { display: none !important; visibility: hidden !important; }
    [data-testid="stAppDeployButton"] { display: none !important; visibility: hidden !important; }

    /* 4. SAĞ ALTTAKİ İZLEYİCİ ROZETİ (Avatar/Viewer Badge) */
    [data-testid="stStatusWidget"] { display: none !important; visibility: hidden !important; }
    div[class^="viewerBadge"] { display: none !important; }

    /* 5. Genel Toolbar ve Dekorasyonlar */
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

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
            # 1. Streamlit Cloud (Secrets)
            if "firebase" in st.secrets:
                key_dict = json.loads(st.secrets["firebase"]["json_content"])
                cred = credentials.Certificate(key_dict)
            # 2. Lokal Test (Dosya)
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
# 🎨 SAYFA AYARLARI
# ==========================================

st.set_page_config(page_title="BIST Yapay Zeka PRO", layout="wide", page_icon="🐋")

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    h1 { color: #00d4ff !important; }
    h2 { color: #ffbd45 !important; border-bottom: 2px solid #ffbd45; padding-bottom: 10px;}
    div[data-testid="stFileUploader"] { margin-bottom: 10px; }
    .stAlert { border-left: 5px solid #ffbd45; }
    div.stButton > button:first-child { font-weight: bold; }
    
    .x-btn, .live-data-btn {
        display: inline-block;
        padding: 12px 20px;
        text-align: center;
        text-decoration: none;
        font-size: 16px;
        border-radius: 8px;
        width: 100%;
        margin-top: 10px;
        font-weight: bold;
        transition: 0.3s;
        color: white !important;
    }
    .x-btn { background-color: #000000; border: 1px solid #333; }
    .x-btn:hover { background-color: #1a1a1a; border-color: #1d9bf0; }
    
    .live-data-btn { background-color: #d90429; border: 1px solid #ef233c; }
    .live-data-btn:hover { background-color: #ef233c; }

    .key-status-pass { color: #00ff00; font-weight: bold; }
    .key-status-fail { color: #ff4444; font-weight: bold; }
    .key-status-limit { color: #ffbd45; font-weight: bold; }

    .element-container:has(> .stJson) { display: none; }
</style>
""", unsafe_allow_html=True)

# --- SESSION INIT ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "is_admin" not in st.session_state: st.session_state.is_admin = False
if "reset_counter" not in st.session_state: st.session_state.reset_counter = 0
if "api_depth_data" not in st.session_state: st.session_state.api_depth_data = None
if "api_akd_data" not in st.session_state: st.session_state.api_akd_data = None
# Telegram Görüntüleri
if "tg_img_derinlik" not in st.session_state: st.session_state.tg_img_derinlik = None
if "tg_img_akd" not in st.session_state: st.session_state.tg_img_akd = None
if "tg_img_kademe" not in st.session_state: st.session_state.tg_img_kademe = None
if "tg_img_takas" not in st.session_state: st.session_state.tg_img_takas = None

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
    
    # 1. Admin Girişi Kontrolü
    if input_pass == admin_secret:
        st.session_state.authenticated = True
        st.session_state.is_admin = True  # Yönetici AÇIK
        return

    # 2. Beta (Normal) Giriş Kontrolü
    if input_pass == correct_password:
        if global_config["beta_active"]:
            st.session_state.authenticated = True
            st.session_state.is_admin = False # 👈 BURASI KRİTİK: Yönetici KAPALI
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
        
        keys_to_keep = ["authenticated", "is_admin", "reset_counter", "api_depth_data", "api_akd_data", "tg_img_derinlik", "tg_img_akd", "tg_img_kademe", "tg_img_takas"]
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
    # 1. HissePlus API
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

# --- DATA STATUS INDICATORS ---
if st.session_state.api_depth_data is not None or st.session_state.api_akd_data is not None:
    st.markdown("##### 📊 Veri Durumu")
    stat_col1, stat_col2 = st.columns(2)
    with stat_col1:
        if st.session_state.api_depth_data: st.success("API DERİNLİK 🟢")
        else: st.error("API DERİNLİK 🔴")
    with stat_col2:
        if st.session_state.api_akd_data: st.success("API AKD 🟢")
        else: st.error("API AKD 🔴")

# --- INIT KEYS ---
api_keys = []
if "GOOGLE_API_KEY" in st.secrets:
    raw = st.secrets["GOOGLE_API_KEY"]
    api_keys = [k.strip() for k in raw.split(",") if k.strip()] if "," in raw else [raw]

if "analysis_result" not in st.session_state: st.session_state.analysis_result = None
if "messages" not in st.session_state: st.session_state.messages = []
if "loaded_count" not in st.session_state: st.session_state.loaded_count = 0
if "active_working_key" not in st.session_state: st.session_state.active_working_key = None

for cat in ["Derinlik", "AKD", "Kademe", "Takas"]:
    if f"pasted_{cat}" not in st.session_state: st.session_state[f"pasted_{cat}"] = []

# --- SIDEBAR & TELEGRAM BRIDGE ---
def fetch_data_via_bridge(symbol, data_type):
    """Firebase üzerinden PC'deki bridge.py ile konuşur"""
    if not firebase_ready:
        st.error("Veritabanı bağlantısı yok.")
        return None

    status_area = st.empty()
    try:
        # 1. EMİR GÖNDER
        status_area.info(f"📡 {symbol} için {data_type} isteniyor... PC'ye bağlanılıyor.")
        
        ref_req = db.reference('bridge/request')
        ref_req.set({
            'symbol': symbol,
            'type': data_type,
            'status': 'pending',
            'timestamp': time.time()
        })
        
        # 2. CEVABI BEKLE (25 Saniye)
        progress_bar = st.progress(0)
        for i in range(25):
            time.sleep(1)
            progress_bar.progress((i + 1) / 25)
            
            status = ref_req.get().get('status')
            
            if status == 'processing':
                status_area.warning("⏳ Robot emri aldı, Telegram'dan yanıt bekleniyor...")
            
            elif status == 'completed':
                status_area.success("✅ Veri Alındı!")
                progress_bar.empty()
                
                # Resmi indir
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

with st.sidebar:
    st.header("🔑 Anahtar Havuzu")
    if st.button("🔄 Anahtarları Test Et"):
        # ... (test kodlarınız aynı kalabilir) ...
        pass # Buraya eski kodlarınız gelecek
    
    st.markdown("---")
    
    # 👇👇👇 GİZLEME KODU BAŞLANGICI 👇👇👇
    # .get() kullanarak hata riskini sıfıra indiriyoruz
    if st.session_state.get("is_admin", False) is True:
        
        st.header("📲 Telegram Köprüsü")
        st.caption("🔒 Sadece Admin Görebilir") # Kontrol amaçlı yazı
        
        tg_ticker = st.text_input("Hisse Kodu (TG):", api_ticker_input, key="tg_ticker").upper()
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            if st.button("📉 Derinlik Verileri Al", key="tg_dr"):
                st.session_state.tg_img_derinlik = fetch_data_via_bridge(tg_ticker, "derinlik")
        with col_t2:
            if st.button("🏦 AKD Verileri Al", key="tg_akd"):
                st.session_state.tg_img_akd = fetch_data_via_bridge(tg_ticker, "akd")
                
        col_t3, col_t4 = st.columns(2)
        with col_t3:
            if st.button("📊 Kademe Verileri Al", key="tg_kdm"):
                st.session_state.tg_img_kademe = fetch_data_via_bridge(tg_ticker, "kademe")
        with col_t4:
            if st.button("🌍 Takas Verileri Al", key="tg_tks"):
                st.session_state.tg_img_takas = fetch_data_via_bridge(tg_ticker, "takas")

        st.markdown("---")
        
        # Yönetici Ayarları da sadece admine görünmeli
        st.subheader("⚙️ Yönetici")
        curr = global_config["beta_active"]
        new_s = st.toggle("Beta Açık", value=curr)
        if new_s != curr:
            global_config["beta_active"] = new_s
            save_global_config(global_config)
            st.rerun()
            
    # 👆👆👆 GİZLEME KODU BİTİŞİ 👆👆👆

    # Çıkış butonu HERKESTE görünmeli (if bloğunun DIŞINDA olmalı)
    if st.button("🚪 Çıkış Yap"):
        st.session_state.authenticated = False
        st.session_state.is_admin = False  # Çıkışta yetkiyi sıfırla
        st.rerun()

with st.sidebar:
    st.markdown("---")
    st.header("𝕏 Tarayıcı")
    raw_ticker = st.text_input("Kod:", api_ticker_input).upper()
    clean_ticker = raw_ticker.replace("#", "").strip()
    
    search_mode = st.radio("Tip:", ("🔥 Geçmiş", "⏱️ Canlı"))
    if search_mode == "🔥 Geçmiş":
        s_date = st.date_input("Tarih", datetime.date.today())
        url = f"https://x.com/search?q={quote(f'#{clean_ticker} lang:tr until:{s_date + datetime.timedelta(days=1)} since:{s_date} min_faves:5')}&src=typed_query&f=top"
        btn_txt = f"🔥 <b>{s_date}</b> Popüler"
    else:
        url = f"https://x.com/search?q={quote(f'#{clean_ticker} lang:tr')}&src=typed_query&f=live"
        btn_txt = f"⏱️ Son Dakika"
    
    st.markdown(f"""<a href="{url}" target="_blank" class="x-btn">{btn_txt}</a>""", unsafe_allow_html=True)

# --- FUNCTIONS ---
valid_model_name = None
working_key = None

def get_model(key):
    try:
        genai.configure(api_key=key)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in models: 
            if "gemini-1.5-flash" in m: return m
        return models[0] if models else None
    except: return None

for k in api_keys:
    mod = get_model(k)
    if mod: 
        valid_model_name = mod
        working_key = k
        break

if not valid_model_name:
    st.error("❌ Aktif Model Bulunamadı.")
    st.stop()

# 🔥 HIZLANDIRMA 1: Görsel Sıkıştırma Fonksiyonu
def compress_image(image, max_size=(800, 800)):
    """Görselleri analiz için küçültür ve hızlandırır"""
    if image.mode in ("RGBA", "P"): image = image.convert("RGB")
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    return image

# --- YENİ HABER ÇEKME ---
def fetch_stock_news(symbol):
    """Google News RSS (Son 24 Saat)"""
    if not NEWS_ENABLED: return "Haber modülü aktif değil (feedparser eksik)."
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

# --- UPLOAD SECTION (OTOMATİK GÖSTERİM EKLENDİ) ---
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
    """Yapıştırılan görselleri ve silme butonlarını gösterir"""
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

# ==========================================
# 🖼️ GÖRSEL YÖNETİM PANELİ
# ==========================================

def render_category_panel(title, cat_name, tg_session_key, uploader_key):
    """Her kategori için standart panel oluşturur"""
    st.markdown(f"### {title}")
    
    # --- 1. TELEGRAM GÖRSELİ ---
    if st.session_state[tg_session_key]:
        with st.container(border=True):
            st.caption("📲 Telegram'dan Alındı")
            st.image(st.session_state[tg_session_key], width=100, caption="TG Verisi") 
            
            if st.button("🗑️ Kaldır", key=f"del_tg_{cat_name}"):
                st.session_state[tg_session_key] = None
                st.rerun()
    
    # --- 2. DOSYA YÜKLEME ---
    uploaded_files = st.file_uploader("Dosya Yükle", type=["jpg","png","jpeg"], key=uploader_key, accept_multiple_files=True)
    
    # --- 3. YAPIŞTIRMA VE GALERİ ---
    handle_paste(cat_name) 
    show_images(cat_name)  
    
    return uploaded_files

# İki Kolonlu Yapı
col1, col2 = st.columns(2)

with col1:
    img_d = render_category_panel("1. Derinlik 💹", "Derinlik", "tg_img_derinlik", f"d_{file_key_suffix}")
    st.markdown("---") 
    img_k = render_category_panel("3. Kademe 📊", "Kademe", "tg_img_kademe", f"k_{file_key_suffix}")

with col2:
    img_a = render_category_panel("2. AKD 🤵", "AKD", "tg_img_akd", f"a_{file_key_suffix}")
    st.markdown("---") 
    img_t = render_category_panel("4. Takas 🌍", "Takas", "tg_img_takas", f"t_{file_key_suffix}")

# --- ANALYZE ---
st.markdown("---")
c1, c2 = st.columns([1, 1])

with c2:
    # MOD SEÇİM EKRANI
    st.markdown("##### 🛠️ Analiz Ayarları")
    analysis_mode = st.radio(
        "Analiz Modu Seçiniz:",
        options=[
            "⚡ SADE MOD (Öz ve Net)", 
            "🛡️ DESTEK-DİRENÇ MODU (Özel Strateji)",
            "🧠 GELİŞMİŞ MOD (Ultra Detay - 50 Madde)"
        ],
        index=0,
        help="Sade Mod: Temel veriler. Destek-Direnç Modu: 15'er adet seviye belirler. Gelişmiş Mod: 50 maddelik mikro analiz."
    )
    
    # Sadece gelişmiş modda slider göster
    if "GELİŞMİŞ" in analysis_mode:
        max_items = st.slider("Gelişmiş Mod Madde Sayısı", 10, 50, 20)
    elif "DESTEK" in analysis_mode:
        st.caption("ℹ️ Destek-Direnç Modu: En az 15 Destek ve 15 Direnç seviyesi detaylıca incelenir.")
    else:
        st.caption("ℹ️ Sade Mod: Her başlık için en az 10 madde analiz edilir.")

with c1:
    st.markdown("<br>", unsafe_allow_html=True)
    # Buton tasarımı
    if st.button("🐋 ANALİZİ BAŞLAT", type="primary", use_container_width=True):
        input_data = []
        
        # --- BİRLEŞTİRİLMİŞ VERİ SETİ ---
        context_str = ""
        # 1. API
        if st.session_state.api_depth_data:
            context_str += f"\n\n--- CANLI DERİNLİK API VERİSİ (HissePlus) ---\n{json.dumps(st.session_state.api_depth_data, indent=2, ensure_ascii=False)}"
        if st.session_state.api_akd_data:
            context_str += f"\n\n--- CANLI AKD API VERİSİ (HissePlus) ---\n{json.dumps(st.session_state.api_akd_data, indent=2, ensure_ascii=False)}"

        # 2. Haberler
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
        
        # --- VERİ VARLIK KONTROLLERİ ---
        is_depth_avail = has_d or st.session_state.api_depth_data
        is_akd_avail = has_a or st.session_state.api_akd_data
        is_kademe_avail = has_k
        is_takas_avail = has_t
        
        # --- PROMPT MİMARİSİ ---
        base_role = f"""
        Sen Borsa Uzmanısın ve Kıdemli Veri Analistisin.
        GÖREV: SADECE sana sağlanan görselleri ve verileri kullanarak analiz yap.
        🚨 Hisse kodunu görselden veya veriden tespit et.
        
        --- MEVCUT VERİ SETİ ---
        {context_str}
        
        --- ⚠️ KRİTİK KURALLAR (HAYATİ ÖNEM TAŞIR) ---
        1. 🚫 **YASAK:** Elimizde verisi olmayan hiçbir başlığı rapora ekleme.
        2. 🚫 **YASAK:** "Mevcut Veri Seti Bilgilendirmesi" veya giriş cümlesi yazma. Direkt analize başla.
        3. 📝 **BİÇİM:** ASLA PARAGRAF YAZMA. Madde madde ilerle.
        4. 🎨 **RENK:** :green[**OLUMLU**], :blue[**NÖTR**], :red[**OLUMSUZ**] kelimeleri / cümleleri vurgula.
        """

        # ==========================================
        # ⚡ SADE MOD PROMPTU
        # ==========================================
        if "SADE" in analysis_mode:
            req_sections = ""
            
            if is_depth_avail:
                req_sections += """
                ## 💹 DERİNLİK ANALİZİ (EN AZ 10 MADDE)
                (Alıcı/Satıcı dengesi, bekleyen emirler, baskı durumu vb.)
                """
            
            if is_akd_avail:
                req_sections += """
                ## 🤵 AKD (ARACI KURUM) ANALİZİ (EN AZ 10 MADDE)
                (Kim alıyor, kim satıyor, maliyetler, toplu/dağınık durumu vb.)
                """
            
            if is_kademe_avail:
                req_sections += """
                ## 📊 KADEME ANALİZİ (EN AZ 10 MADDE)
                (İşlem yoğunluğu, aktif alıcılar, pasif satıcılar, işlem geçen fiyatlar vb.)
                """
            
            if is_takas_avail:
                req_sections += """
                ## 🌍 TAKAS ANALİZİ (EN AZ 10 MADDE)
                (Yabancı durumu, haftalık değişimler, saklama oranları vb.)
                """

            prompt = base_role + f"""
            --- ⚡ SADE MOD SEÇİLDİ ---
            {req_sections}

            ## 🛡️ GÜÇLÜ/ZAYIF DESTEK VE DİRENÇ ANALİZİ
            (Grafik ve derinlik verilerine bakarak EN AZ 10 ADET Destek seviyesi ve EN AZ 10 ADET Direnç seviyesi yaz.)
            * :green[**Destekler:** ...]
            * :red[**Dirençler:** ...]

            ## 🐋 GENEL SENTEZ (BALİNA İZİ)
            (Büyük oyuncuların ne yapmaya çalıştığını madde madde özetle. En az 10 madde.)

            ## 7. 🧭 YÖN / FİYAT OLASILIĞI (DETAYLI SENARYO)
            * **📈 Yükseliş İhtimali:** %...
            * **📉 Düşüş İhtimali:** %...
            * **Hedef Fiyatlar ve Stop Bölgeleri:** ...

            ## 8. 💯 SKOR KARTI (TABLO)
            (Markdown Tablosu olarak yap. Sadece verisi olanları ekle.)
            | Parametre | Durum | Puan (0-10) |
            |---|---|---|
            | (Mevcut Veriler) | ... | ... |

            ## 9. 🚀 İŞLEM PLANI (STRATEJİ)
            """

        # ==========================================
        # 🛡️ DESTEK-DİRENÇ ÖZEL MODU (YENİ EKLENDİ)
        # ==========================================
        elif "DESTEK" in analysis_mode:
            prompt = base_role + f"""
            --- 🛡️ DESTEK-DİRENÇ VE SEVİYE ANALİZİ MODU ---
            GÖREV: Bu modda SADECE kritik fiyat seviyelerine ve bu seviyelerin neden önemli olduğuna odaklan.
            Laf kalabalığı yapma, nokta atışı rakamlar ver.

            ## 🧱 KRİTİK DESTEK BÖLGELERİ (EN AZ 15 ADET)
            (Elindeki derinlik, kademe ve AKD verilerini kullanarak EN AZ 15 tane destek noktası belirle.)
            (HER MADDEDE MUTLAKA AÇIKLAMA OLACAK: Neden burası destek? "Çok güçlü alış bölgesi", "Fiyat buradan sürekli dönüyor", "Derinlikte 1M lot alıcı var" gibi detaylar ver.)
            1. **[FİYAT]** - [GÜÇ DERECESİ]: ...
            2. **[FİYAT]** - [GÜÇ DERECESİ]: ...
            ... (15 maddeye tamamla)

            ## 🚧 KRİTİK DİRENÇ BÖLGELERİ (EN AZ 15 ADET)
            (Elindeki verilere göre EN AZ 15 tane direnç/satış noktası belirle.)
            (HER MADDEDE AÇIKLAMA YAP: "Burada satış duvarı var", "Maliyetlenme burada yoğun", "Psikolojik sınır" gibi.)
            1. **[FİYAT]** - [GÜÇ DERECESİ]: ...
            2. **[FİYAT]** - [GÜÇ DERECESİ]: ...
            ... (15 maddeye tamamla)

            ## ⚖️ KİLİT RAKAM (PİVOT)
            Hissenin "Tamam mı devam mı" dediği o tek rakam hangisi?

            ## 📉 GAP (BOŞLUK) ANALİZİ
            Fiyat hareketlerinde kapatılmayı bekleyen GAP (boşluk) var mı?

            ## 🚀 ALIM-SATIM STRATEJİSİ
            Bu seviyelere göre;
            * Nereden güvenli alım yapılır?
            * Stop-loss nereye konulmalı? (Hangi desteğin kırılımı tehlikeli?)
            * Kar al (Take-Profit) noktaları neresi?
            """

        # ==========================================
        # 🧠 GELİŞMİŞ MOD PROMPTU
        # ==========================================
        else:
            limit_txt = f"(DİKKAT: EN AZ {max_items} TANE MADDELİ ANALİZ YAP.)"
            
            # Dinamik Ana Başlıklar
            main_headers = ""
            if is_depth_avail: main_headers += f"## 📸 DERİNLİK ANALİZİ {limit_txt}\n"
            if is_akd_avail: main_headers += f"## 🏦 AKD ANALİZİ {limit_txt}\n"
            if is_kademe_avail: main_headers += f"## 📊 KADEME ANALİZİ {limit_txt}\n"
            if is_takas_avail: main_headers += f"## 🌍 TAKAS ANALİZİ {limit_txt}\n"

            prompt = base_role + f"""
            
            --- 🧠 GELİŞMİŞ (ULTRA DETAY) MOD SEÇİLDİ ---
            
            --- İSTENEN RAPOR BAŞLIKLARI ---
            {main_headers}

            --- 🕵️‍♂️ MİKRO-YAPISAL ANALİZ ---
            GÖREV: Aşağıdaki 50 maddelik detaylı kontrol listesini taramanı istiyorum.
            ANCAK: **SADECE ELİMİZDEKİ GÖRSELLERDE CEVABI OLAN MADDELERİ RAPORA YAZ.**
            ❌ Eğer bir maddenin cevabı görsellerde/verilerde yoksa, o maddeyi rapora HİÇ YAZMA, ATLA. Boşuna "Veri yok" deme.
            
            (Kontrol Listesi):
            1. 💰 GÜNÜN AĞIRLIKLI MALİYET ANALİZİ (KADEME): Fiyat yoğunluk bölgesinin neresinde?
            2. 🤖 ROBOT VE ALGORİTMA TARAYICISI (AKD): BofA, İnfo, Yatırım Finansman devrede mi?
            3. 👑 TAHTA YAPICININ KAR/ZARAR DURUMU: En çok alan kurum karda mı zararda mı?
            4. 🎭 ALGI YÖNETİMİ & TUZAK RADARI: Derinlikteki emirler gerçek mi, siliniyor mu?
            5. 🥊 "DİĞER"LER SAVAŞI (AKD): Küçük yatırımcı (Diğer) alıyor mu satıyor mu?
            6. 🏦 TAKAS - AKD UYUMSUZLUĞU: Alan kurum saklamada malı tutuyor mu?
            7. 🕵️‍♂️ VİRMANLI ALIM TESPİTİ: Takas ile AKD arasında virman şüphesi var mı?
            8. 📊 TAKAS KONSANTRASYONU: Mal ne kadar toplu? (İlk 5 kurum oranı)
            9. 🧱 SATIŞ DUVARI VE PSİKOLOJİK DİRENÇ: Derinlikte nerede blok satış var?
            10. 🌡️ ANLIK BASKI DENGESİ: Derinlikte alıcılar mı istekli satıcılar mı?
            11. ⚖️ AOF (AĞIRLIKLI ORTALAMA) SAPMASI: Fiyat AOF'un altında mı üstünde mi?
            12. ✂️ MAKAS (SPREAD) VE LİKİDİTE RİSKİ: Kademe aralıkları açık mı?
            13. 🏹 AGRESİF vs. PASİF İŞLEM: İşlemler aktiften (satış kademesinden) mi geçiyor?
            14. 🐋 LOT BÜYÜKLÜĞÜ ANALİZİ: Kademede geçen lotlar büyük mü (Balina) küçük mü?
            15. 🕳️ KADEMELERDEKİ 'HAVA BOŞLUKLARI': Alt kademeler dolu mu boş mu?
            16. ⚔️ ALICI / SATICI GÜÇ RASYOSU (AKD): İlk 5 Alıcı / İlk 5 Satıcı oranı.
            17. 📍 POC (POINT OF CONTROL): En çok işlem hacminin geçtiği fiyat seviyesi.
            18. 🧠 PSİKOLOJİK RAKAM SAVAŞLARI: .00 veya .50'li seviyelerde yığılma var mı?
            19. 🤝 EKÜRİ (PASLAŞAN) KURUMLAR: BofA ile YK veya Info beraber mi hareket ediyor?
            20. 📉 PANİK SATIŞI İZLERİ: Kademede küçük lotlarla şelale düşüşü var mı?
            21. 🕒 KREDİLİ İŞLEM KURUMLARI: A1, Marbaş, Osmanlı, Info ne yönde işlem yapıyor?
            22. 🪜 MERDİVEN (STEP-UP) DESTEK: Alış emirleri fiyata yakınlaşarak mı geliyor?
            23. 🩸 DİPTEN DÖNÜŞ VAR MI? Günün en düşüğünden tepki gelmiş mi?
            24. 🧢 TAVAN / TABAN KİLİT POTANSİYELİ: Tavan/Taban kademesinde ne kadar lot var?
            25. 🧬 GERÇEK YABANCI MI, BIYIKLI YABANCI MI? Takas değişimleri ne diyor?
            26. 🏎️ İŞLEM YOĞUNLUĞU GÖRSELİ: İşlemler ne kadar sık geçiyor?
            27. 🧱 BLOK SATIŞ KARŞILAMA: Büyük satışlar hemen karşılanıyor mu?
            28. ⚖️ ORTALAMA MALİYET YÜKSELTME (MARKUP): Fiyat yükselirken hacim artıyor mu?
            29. 🧮 GİZLİ TOPLAMA OPERASYONU: AKD'de dağınık alım, Takasta toplu birikim var mı?
            30. 🏛️ KURUM KARAKTER ANALİZİ: Oyuncular trader mı yoksa kurumsal mı?
            31. 🧊 GİZLİ EMİR (ICEBERG) TESPİTİ: Görünenden daha fazla işlem geçiyor mu?
            32. 🌪️ HACİM / FİYAT UYUMSUZLUĞU (CHURNING): Hacim var ama fiyat gitmiyor mu?
            33. 🚫 ALIM/SATIM İPTALİ: Derinlikte iptal edilen emirler var mı?
            34. 🔄 GÜN İÇİ DÖNÜŞ (REVERSAL) SİNYALİ: Mum veya kademe dönüş işareti veriyor mu?
            35. 💰 NET PARA GİRİŞ/ÇIKIŞ GÖRÜNTÜSÜ: Para girişi pozitif mi?
            36. 📉 GAP (FİYAT BOŞLUĞU) RİSKİ: Haber veya açılış kaynaklı boşluk var mı?
            37. 🛡️ PİVOT SEVİYESİ KONUMU: Fiyat pivotun neresinde?
            38. 🎢 KADEME DOLULUĞU: Tahta sığ mı (manipülasyona açık) yoksa derin mi?
            39. 🏦 BANK OF AMERICA (BofA) ETKİSİ: Tahtayı tek başına mı domine ediyor?
            40. ⏳ KAPANIŞA DOĞRU DURUM: Gün sonu risk iştahı nasıl?
            41. ♻️ DEVİR HIZI (TURNOVER): Takastaki mal ne kadar el değiştirmiş?
            42. 🕸️ DESTEK ALTI İŞLEM HACMİ: Destek kırılınca hacim artmış mı (Stop patlatma)?
            43. 📅 TAKAS SAKLAMA DEĞİŞİMİ: Haftalık/Aylık değişimde kim topluyor?
            44. 📊 ENDEKSE DUYARLILIK: Endeks hareketine tepkisi nasıl?
            45. 📐 DERİNLİK EĞİM (SLOPE) ANALİZİ: Alış tarafı mı daha dik, satış tarafı mı?
            46. 🌑 KARANLIK ODA TAHMİNİ: Eşleşme fiyatı teorik olarak nerede?
            47. 🕯️ İŞLEM SIKLIĞI (YOĞUNLUK): Trade sıklığı robot varlığına işaret ediyor mu?
            48. 🏗️ KURUMSAL vs. BİREYSEL SAVAŞI: Kim daha baskın?
            49. 🚩 GÜN İÇİ FORMASYON: Bayrak, Flama, OBO vb. mikro formasyon var mı?
            50. 💎 ELMAS DEĞERİNDE SON SÖZ: Tüm bunlara göre TEK CÜMLE: Yön neresi?

            --- FİNAL ---
            ## 🐋 GENEL SENTEZ
            ## 🧭 YÖN / FİYAT OLASILIĞI
            ## 💯 SKOR KARTI & TRENDMETRE (TABLO - Sadece Verisi Olanlar)
            ## 🚀 İŞLEM PLANI
            """
        input_data.append(prompt)
        
        # Eğer ne görsel ne API yoksa
        count = 0
        if has_d: count += 1
        if has_a: count += 1
        if has_k: count += 1
        if has_t: count += 1
        
        if count == 0 and not context_str:
            st.warning("⚠️ Lütfen analiz için veri yükleyin (Görsel, API veya Telegram).")
        else:
            # 🔥 HIZLANDIRMA 2: Streaming (Canlı Akış)
            # Spinner yerine canlı yazı akışı
            placeholder = st.empty()
            full_response = ""
            
            with st.spinner("Analiz Başlatılıyor... (Akış birazdan başlayacak)"):
                try:
                    # Key Döngüsü ve Streaming Mantığı
                    stream_active = False
                    
                    # Keyleri karıştır ki hep aynı keye yük binmesin
                    local_keys = api_keys.copy()
                    if working_key in local_keys:
                        local_keys.remove(working_key)
                        local_keys.insert(0, working_key)
                        
                    for k in local_keys:
                        try:
                            genai.configure(api_key=k)
                            model = genai.GenerativeModel(valid_model_name)
                            # STREAMING AÇIK
                            stream = model.generate_content(input_data, stream=True)
                            
                            st.session_state.active_working_key = k
                            working_key = k
                            stream_active = True
                            
                            # Akış Başlıyor
                            for chunk in stream:
                                if chunk.text:
                                    full_response += chunk.text
                                    placeholder.markdown(full_response + "▌") # İmleç efekti
                            
                            placeholder.markdown(full_response) # Son hali
                            st.session_state.analysis_result = full_response
                            st.session_state.loaded_count = count
                            break # Başarılı olduysa döngüden çık
                            
                        except Exception as e:
                            if "429" in str(e) or "quota" in str(e).lower(): continue
                            else: st.error(f"Hata: {e}"); break
                    
                    if not stream_active:
                         st.error("Tüm kotalar dolu veya bağlantı hatası.")
                         
                except Exception as e:
                    st.error(f"Genel Hata: {e}")

# ==========================================
# 💬 SONUÇ VE SOHBET (FİNAL BÖLÜMÜ)
# ==========================================
if st.session_state.analysis_result:
    if not 'placeholder' in locals():
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
            try:
                sys_inst = (
                    "GÖREV: Sadece rapora sadık kal." if chat_scope == "📝 RAPOR" 
                    else "GÖREV: Raporu temel al ama genel borsa bilginle yorum kat."
                )
                final_prompt = f"{sys_inst}\n\nRAPOR:\n{st.session_state.analysis_result}\n\nSORU:\n{q}"
                
                genai.configure(api_key=st.session_state.active_working_key)
                model = genai.GenerativeModel(valid_model_name)
                stream = model.generate_content(final_prompt, stream=True)
                
                def parser():
                    for ch in stream: 
                        if ch.text: yield ch.text
                
                resp = st.write_stream(parser)
                st.session_state.messages.append({"role": "assistant", "content": resp})
            except Exception as e: st.error(f"Hata: {e}")






