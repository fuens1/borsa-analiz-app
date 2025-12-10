import streamlit as st
from PIL import Image
import google.generativeai as genai
import datetime
import time
import io
import json
import os
import requests
import pandas as pd
import base64
from urllib.parse import quote

# Kütüphane Kontrolleri
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

try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_ENABLED = True
except ImportError:
    FIREBASE_ENABLED = False

# ==========================================
# 🔐 AYARLAR VE FIREBASE
# ==========================================
CONFIG_FILE = "site_config.json"
FIREBASE_DB_URL = 'https://borsakopru-default-rtdb.firebaseio.com/' 

def init_firebase():
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
    except: return False

firebase_ready = init_firebase()

def load_global_config():
    try:
        with open(CONFIG_FILE, "r") as f: return json.load(f)
    except: return {"beta_active": True}

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
    div.stButton > button:first-child { font-weight: bold; }
    .x-btn { background-color: #000000; color: white !important; border: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

# --- SESSION INIT ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "is_admin" not in st.session_state: st.session_state.is_admin = False
if "reset_counter" not in st.session_state: st.session_state.reset_counter = 0
if "api_depth_data" not in st.session_state: st.session_state.api_depth_data = None
if "api_akd_data" not in st.session_state: st.session_state.api_akd_data = None
if "tg_img_derinlik" not in st.session_state: st.session_state.tg_img_derinlik = None
if "tg_img_akd" not in st.session_state: st.session_state.tg_img_akd = None
if "tg_img_kademe" not in st.session_state: st.session_state.tg_img_kademe = None
if "tg_img_takas" not in st.session_state: st.session_state.tg_img_takas = None
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# --- AUTH ---
query_params = st.query_params
admin_secret = st.secrets.get("ADMIN_KEY", "admin123") 

if query_params.get("admin") == admin_secret:
    st.session_state.authenticated = True
    st.session_state.is_admin = True

def check_password():
    input_pass = st.session_state.get("password_input", "")
    if input_pass == admin_secret:
        st.session_state.authenticated = True
        st.session_state.is_admin = True
    elif input_pass == st.secrets.get("APP_PASSWORD"):
        if global_config["beta_active"]:
            st.session_state.authenticated = True
            st.session_state.is_admin = False
        else: st.error("🔒 Kapalı.")
    elif input_pass: st.error("❌ Hatalı.")

if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔒 Giriş")
        if global_config["beta_active"]:
            st.text_input("Kod:", type="password", key="password_input", on_change=check_password)
            if st.button("Giriş"): check_password()
        else:
            with st.expander("Yönetici"):
                st.text_input("Admin:", type="password", key="password_input", on_change=check_password)
                if st.button("Giriş"): check_password()
    st.stop()

# ==========================================
# 🚀 MAIN APP
# ==========================================
col_title, col_reset = st.columns([5, 1])
with col_title:
    st.title("🐋 BIST Yapay Zeka PRO")
with col_reset:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 SIFIRLA", type="secondary"):
        st.session_state.reset_counter += 1
        # Reset logic... (Kısaltıldı)
        for key in list(st.session_state.keys()):
            if key not in ["authenticated", "is_admin", "reset_counter", "chat_history"]:
                del st.session_state[key]
        for cat in ["Derinlik", "AKD", "Kademe", "Takas"]:
            st.session_state[f"pasted_{cat}"] = []
        st.rerun()

# --- API ---
st.markdown("---")
col_api1, col_api2 = st.columns([3, 1])
with col_api1: api_ticker = st.text_input("Hisse:", "THYAO").upper()
with col_api2: 
    st.markdown("<br>", unsafe_allow_html=True)
    fetch_btn = st.button("API Verisi Çek", type="primary")

if fetch_btn:
    try:
        today = datetime.date.today().strftime("%Y-%m-%d")
        h = {'User-Agent': 'Mozilla/5.0'}
        with st.spinner("Çekiliyor..."):
            r_d = requests.get(f"https://webapi.hisseplus.com/api/v1/kademe?sembol={api_ticker}", headers=h)
            st.session_state.api_depth_data = r_d.json() if r_d.status_code == 200 else None
            r_a = requests.get(f"https://webapi.hisseplus.com/api/v1/akd?sembol={api_ticker}&ilk={today}&son={today}", headers=h)
            st.session_state.api_akd_data = r_a.json() if r_a.status_code == 200 else None
    except: st.error("API Hatası")

# Status
if st.session_state.api_depth_data or st.session_state.api_akd_data:
    c1, c2 = st.columns(2)
    c1.success("DERİNLİK 🟢") if st.session_state.api_depth_data else c1.error("DERİNLİK 🔴")
    c2.success("AKD 🟢") if st.session_state.api_akd_data else c2.error("AKD 🔴")

# --- INIT KEYS ---
api_keys = [k.strip() for k in st.secrets.get("GOOGLE_API_KEY", "").split(",") if k.strip()]
if "active_working_key" not in st.session_state: st.session_state.active_working_key = None
if "analysis_result" not in st.session_state: st.session_state.analysis_result = None

for cat in ["Derinlik", "AKD", "Kademe", "Takas"]:
    if f"pasted_{cat}" not in st.session_state: st.session_state[f"pasted_{cat}"] = []

# --- TELEGRAM BRIDGE ---
def fetch_tg(symbol, dtype):
    if not firebase_ready: return None
    try:
        ref = db.reference('bridge/request')
        ref.set({'symbol': symbol, 'type': dtype, 'status': 'pending', 'timestamp': time.time()})
        bar = st.progress(0)
        for i in range(25):
            time.sleep(1); bar.progress((i+1)/25)
            stat = ref.get().get('status')
            if stat == 'completed':
                data = db.reference('bridge/response').get()
                bar.empty()
                return Image.open(io.BytesIO(base64.b64decode(data['image_base64'])))
    except: pass
    return None

with st.sidebar:
    st.header("📲 Telegram")
    tg_sym = st.text_input("Kod (TG):", api_ticker).upper()
    c1, c2 = st.columns(2)
    if c1.button("📉 Derinlik"): st.session_state.tg_img_derinlik = fetch_tg(tg_sym, "derinlik")
    if c2.button("🏦 AKD"): st.session_state.tg_img_akd = fetch_tg(tg_sym, "akd")
    c3, c4 = st.columns(2)
    if c3.button("📊 Kademe"): st.session_state.tg_img_kademe = fetch_tg(tg_sym, "kademe")
    if c4.button("🌍 Takas"): st.session_state.tg_img_takas = fetch_tg(tg_sym, "takas")

# --- MODELS ---
valid_model = None
for k in api_keys:
    try:
        genai.configure(api_key=k)
        if "gemini-1.5-flash" in [m.name for m in genai.list_models()]: valid_model = "gemini-1.5-flash"; break
    except: continue

if not valid_model: st.error("Model yok."); st.stop()

def compress(img):
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail((800, 800)); return img

def fetch_news(sym):
    if not NEWS_ENABLED: return ""
    try:
        f = feedparser.parse(f"https://news.google.com/rss/search?q={sym}+Borsa+KAP+when:1d&hl=tr&gl=TR&ceid=TR:tr")
        return "\n".join([f"- {e.title}" for e in f.entries[:5]])
    except: return ""

# --- UPLOAD & DISPLAY ---
def render_panel(title, cat, tg_key, key_suffix):
    st.markdown(f"### {title}")
    if st.session_state[tg_key]: st.image(st.session_state[tg_key], width=150, caption="Telegram")
    handle_paste(cat)
    if st.session_state[f"pasted_{cat}"]:
        c = st.columns(3)
        for i, img in enumerate(st.session_state[f"pasted_{cat}"]): c[i%3].image(img, width=100)
    st.file_uploader("Yükle", key=f"up_{cat}_{key_suffix}")

col1, col2 = st.columns(2)
with col1:
    render_panel("1. Derinlik", "Derinlik", "tg_img_derinlik", st.session_state.reset_counter)
    render_panel("3. Kademe", "Kademe", "tg_img_kademe", st.session_state.reset_counter)
with col2:
    render_panel("2. AKD", "AKD", "tg_img_akd", st.session_state.reset_counter)
    render_panel("4. Takas", "Takas", "tg_img_takas", st.session_state.reset_counter)

def handle_paste(cat):
    if PASTE_ENABLED:
        r = paste_image_button("Yapıştır", key=f"paste_{cat}_{st.session_state.reset_counter}")
        if r.image_data is not None: st.session_state[f"pasted_{cat}"].append(r.image_data)

# --- ANALYZE SECTION ---
st.markdown("---")
ac1, ac2 = st.columns([1, 1])
with ac2:
    analysis_mode = st.radio("Analiz Modu:", ["🌟 SADE MOD (Temel)", "🚀 DETAYLI PRO MOD (Full)"])

with ac1:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🐋 ANALİZİ BAŞLAT", type="primary", use_container_width=True):
        inputs = []
        ctx = ""
        if st.session_state.api_depth_data: ctx += f"\nAPI DERİNLİK: {json.dumps(st.session_state.api_depth_data)}"
        if st.session_state.api_akd_data: ctx += f"\nAPI AKD: {json.dumps(st.session_state.api_akd_data)}"
        if NEWS_ENABLED: ctx += f"\nHABERLER: {fetch_news(api_ticker)}"

        def add(l, t): 
            if l: [inputs.append(compress(Image.open(f))) for f in l if f]; return True
            if t: inputs.append(compress(t)); return True
            return False

        has_d = add(st.session_state[f"pasted_Derinlik"], st.session_state.tg_img_derinlik)
        has_a = add(st.session_state[f"pasted_AKD"], st.session_state.tg_img_akd)
        
        # PROMPT SEÇİMİ
        if "SADE" in analysis_mode:
            # --- SADE MOD PROMPTU ---
            prompt = f"""
            Sen Borsa Uzmanısın. Verilenleri analiz et.
            VERİLER: {ctx}
            
            RAPOR FORMATI:
            ## 💹 DERİNLİK & AKD & TAKAS ANALİZİ
            (Kısa ve öz, önemli noktalar. Renkli: :green[], :red[])
            
            ## 📰 HABER VE GÜNDEM YORUMU
            (Varsa haberlerin etkisi)
            
            ## 🛡️ GÜÇLÜ/ZAYIF DESTEK VE DİRENÇLER
            (En az 5-6 seviye yaz. Kritik yerleri belirt.)
            
            ## 💯 SKOR KARTI & TRENDMETRE
            (Tablo halinde: Parametre | Durum | Puan)
            
            ## 🚀 İŞLEM PLANI (SONUÇ)
            (Al/Sat/Tut stratejisi)
            """
        else:
            # --- DETAYLI PRO MOD PROMPTU ---
            prompt = f"""
            Sen Kıdemli Borsa Analistisin. Detaylı, 50 maddelik kontrol listesiyle analiz yap.
            VERİLER: {ctx}
            
            RAPOR FORMATI:
            1. Önceki tüm görsellerin (Derinlik, AKD, Kademe, Takas) detaylı analizi. (Her başlık altına EN AZ 5 MADDE).
            2. Renkleri kullan: :green[OLUMLU], :red[OLUMSUZ], :blue[NÖTR].
            
            --- 🕵️‍♂️ MİKRO-YAPISAL ANALİZ KONTROL LİSTESİ ---
            (Aşağıdaki maddeleri tek tek incele ve yorumla)
            1. Günün Ağırlıklı Maliyet Analizi
            2. Robot ve Algoritma Takibi
            3. Tahta Yapıcı Durumu
            4. Küçük Yatırımcı (Diğer) Durumu
            5. Takas - AKD Uyumsuzluğu
            6. Virmanlı Alım Tespiti
            7. Takas Konsantrasyonu
            8. Satış Duvarı ve Dirençler
            9. Anlık Baskı Dengesi
            10. Makas ve Likidite
            11. Agresif vs Pasif İşlem
            12. Lot Büyüklüğü (Balina İzi)
            13. Kademelerdeki Hava Boşlukları
            14. Alıcı/Satıcı Güç Rasyosu
            15. POC (Point of Control) Analizi
            16. Psikolojik Rakam Savaşları
            17. Eküri Kurumlar
            18. Panik Satışı İzleri
            19. Kredili İşlem Kurumları
            20. Merdiven Destek Analizi
            21. Dipten Dönüş Sinyali
            22. Tavan/Taban Kilit Potansiyeli
            23. Gerçek vs Bıyıklı Yabancı
            24. İşlem Yoğunluğu Görseli
            25. Blok Satış Karşılama
            26. Markup (Maliyet Yükseltme)
            27. Gizli Toplama
            28. Kurum Karakter Analizi
            29. Gizli Emir (Iceberg) Tespiti
            30. Hacim/Fiyat Uyumsuzluğu
            31. Gün İçi Dönüş (Reversal)
            32. Net Para Giriş/Çıkış
            33. Gap (Boşluk) Riski
            34. Pivot Seviyesi
            35. Kademe Doluluğu
            36. BofA Etkisi
            37. Kapanışa Doğru Durum
            38. Devir Hızı
            39. Destek Altı Hacim
            40. Takas Saklama Değişimi
            41. Derinlik Eğim (Slope)
            42. İşlem Sıklığı
            43. Kurumsal vs Bireysel
            44. Elmas Değerinde Son Söz
            
            --- SONUÇ BÖLÜMÜ ---
            ## 📰 HABER ANALİZİ
            ## 🛡️ DESTEK VE DİRENÇLER (EN AZ 5 SEVİYE)
            ## 🐋 GENEL SENTEZ
            ## 🌡️ PİYASA DUYGU ÖLÇER
            ## 🧭 FİYAT VE YÖN SENARYOSU
            ## 💯 SKOR KARTI (TABLO)
            ## 🚀 İŞLEM PLANI
            """
        
        inputs.append(prompt)
        
        with st.spinner("Analiz yapılıyor..."):
            try:
                # Key Rotation
                keys = api_keys.copy()
                if st.session_state.active_working_key in keys:
                    keys.remove(st.session_state.active_working_key)
                    keys.insert(0, st.session_state.active_working_key)
                
                response_text = ""
                placeholder = st.empty()
                
                for k in keys:
                    try:
                        genai.configure(api_key=k)
                        model = genai.GenerativeModel(valid_model)
                        stream = model.generate_content(inputs, stream=True)
                        for chunk in stream:
                            if chunk.text:
                                response_text += chunk.text
                                placeholder.markdown(response_text + "▌")
                        st.session_state.active_working_key = k
                        st.session_state.analysis_result = response_text
                        placeholder.markdown(response_text)
                        break
                    except Exception as e:
                        if "429" in str(e): continue
                        else: st.error(str(e)); break
            except: pass

# --- RESULT & CHAT ---
if st.session_state.analysis_result:
    st.markdown("---")
    st.header("💬 Analist ile Sohbet")
    
    # Chat Geçmişi Gösterimi
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Chat Input
    if user_input := st.chat_input("Bu analizle ilgili sorunuz? (Örn: Stop seviyesi neresi?)"):
        # Kullanıcı mesajını ekle ve göster
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"): st.markdown(user_input)
        
        # Asistan Cevabı
        with st.chat_message("assistant"):
            try:
                genai.configure(api_key=st.session_state.active_working_key)
                chat_model = genai.GenerativeModel(valid_model)
                
                # Chat Context'i oluştur (Analiz sonucu + Geçmiş)
                history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat_history[-5:]])
                chat_prompt = f"""
                BAĞLAM: Aşağıdaki borsa analiz raporuna göre kullanıcının sorusunu cevapla.
                ANALİZ RAPORU: {st.session_state.analysis_result}
                
                KONUŞMA GEÇMİŞİ:
                {history_text}
                
                KULLANICI SORUSU: {user_input}
                """
                
                stream = chat_model.generate_content(chat_prompt, stream=True)
                response_buffer = ""
                resp_container = st.empty()
                
                for chunk in stream:
                    if chunk.text:
                        response_buffer += chunk.text
                        resp_container.markdown(response_buffer + "▌")
                
                resp_container.markdown(response_buffer)
                st.session_state.chat_history.append({"role": "assistant", "content": response_buffer})
                
            except Exception as e:
                st.error(f"Hata: {e}")
