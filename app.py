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
# 🛠️ KÜTÜPHANE KONTROLLERİ
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

try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_ENABLED = True
except ImportError:
    FIREBASE_ENABLED = False

# ==========================================
# 🔐 AYARLAR VE BAĞLANTILAR
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
    except Exception as e:
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
        display: inline-block; padding: 12px 20px; text-align: center;
        text-decoration: none; font-size: 16px; border-radius: 8px;
        width: 100%; margin-top: 10px; font-weight: bold; transition: 0.3s; color: white !important;
    }
    .x-btn { background-color: #000000; border: 1px solid #333; }
    .x-btn:hover { background-color: #1a1a1a; border-color: #1d9bf0; }
    .live-data-btn { background-color: #d90429; border: 1px solid #ef233c; }
    .live-data-btn:hover { background-color: #ef233c; }

    .key-status-pass { color: #00ff00; font-weight: bold; }
    .key-status-fail { color: #ff4444; font-weight: bold; }
    .element-container:has(> .stJson) { display: none; }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATES ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "is_admin" not in st.session_state: st.session_state.is_admin = False
if "reset_counter" not in st.session_state: st.session_state.reset_counter = 0
if "api_depth_data" not in st.session_state: st.session_state.api_depth_data = None
if "api_akd_data" not in st.session_state: st.session_state.api_akd_data = None
if "analysis_result" not in st.session_state: st.session_state.analysis_result = None
if "messages" not in st.session_state: st.session_state.messages = []
if "active_working_key" not in st.session_state: st.session_state.active_working_key = None

# Telegram Resimleri
for img_key in ["tg_img_derinlik", "tg_img_akd", "tg_img_kademe", "tg_img_takas"]:
    if img_key not in st.session_state: st.session_state[img_key] = None

# Yapıştırılan Resimler
for cat in ["Derinlik", "AKD", "Kademe", "Takas"]:
    if f"pasted_{cat}" not in st.session_state: st.session_state[f"pasted_{cat}"] = []

# --- AUTHENTICATION ---
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
# 🚀 ANA UYGULAMA BAŞLANGICI
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
        st.session_state.analysis_result = None
        st.session_state.messages = []
        for key in ["tg_img_derinlik", "tg_img_akd", "tg_img_kademe", "tg_img_takas"]:
            st.session_state[key] = None
        for cat in ["Derinlik", "AKD", "Kademe", "Takas"]:
            st.session_state[f"pasted_{cat}"] = []
        st.rerun()

# --- API & VERİ MERKEZİ ---
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
            url_depth = f"https://webapi.hisseplus.com/api/v1/derinlik?sembol={api_ticker_input}" # URL düzeltildi
            r_depth = requests.get(url_depth, headers=headers)
            st.session_state.api_depth_data = r_depth.json() if r_depth.status_code == 200 else None
            
            url_akd = f"https://webapi.hisseplus.com/api/v1/akd?sembol={api_ticker_input}&ilk={today_str}&son={today_str}"
            r_akd = requests.get(url_akd, headers=headers)
            st.session_state.api_akd_data = r_akd.json() if r_akd.status_code == 200 else None
    except Exception as e:
        st.error(f"API Hatası: {e}")

# Veri Durumu Göstergeleri
if st.session_state.api_depth_data or st.session_state.api_akd_data:
    st.markdown("##### 📊 Veri Durumu")
    stat_col1, stat_col2 = st.columns(2)
    with stat_col1:
        if st.session_state.api_depth_data: st.success("API DERİNLİK 🟢")
        else: st.error("API DERİNLİK 🔴")
    with stat_col2:
        if st.session_state.api_akd_data: st.success("API AKD 🟢")
        else: st.error("API AKD 🔴")

# --- API KEY HAZIRLIĞI ---
api_keys = []
if "GOOGLE_API_KEY" in st.secrets:
    raw = st.secrets["GOOGLE_API_KEY"]
    api_keys = [k.strip() for k in raw.split(",") if k.strip()] if "," in raw else [raw]

# Geçerli Model Bulma
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

# --- YARDIMCI FONKSİYONLAR ---
def compress_image(image, max_size=(800, 800)):
    if image.mode in ("RGBA", "P"): image = image.convert("RGB")
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    return image

def fetch_stock_news(symbol):
    if not NEWS_ENABLED: return "Haber modülü aktif değil."
    try:
        query = f"{symbol} Borsa KAP when:1d"
        rss_url = f"https://news.google.com/rss/search?q={quote(query)}&hl=tr&gl=TR&ceid=TR:tr"
        feed = feedparser.parse(rss_url)
        news_list = [f"- {e.title} ({time.strftime('%d.%m.%Y %H:%M', e.published_parsed)})" for e in feed.entries[:5]]
        return "\n".join(news_list) if news_list else "Haber yok."
    except: return "Haber hatası."

# --- TELEGRAM KÖPRÜ FONKSİYONU ---
def fetch_data_via_bridge(symbol, data_type):
    if not firebase_ready:
        st.error("Veritabanı yok.")
        return None
    status_area = st.empty()
    try:
        status_area.info(f"📡 {symbol} - {data_type} isteniyor...")
        ref_req = db.reference('bridge/request')
        ref_req.set({'symbol': symbol, 'type': data_type, 'status': 'pending', 'timestamp': time.time()})
        
        progress_bar = st.progress(0)
        for i in range(25):
            time.sleep(1)
            progress_bar.progress((i+1)/25)
            status = ref_req.get().get('status')
            if status == 'completed':
                status_area.success("✅ Veri Alındı!")
                progress_bar.empty()
                data = db.reference('bridge/response').get()
                if data and 'image_base64' in data:
                    return Image.open(io.BytesIO(base64.b64decode(data['image_base64'])))
                break
            elif status == 'timeout':
                status_area.error("❌ Zaman Aşımı"); break
    except Exception as e: status_area.error(f"Hata: {e}")
    return None

# --- SIDEBAR (TELEGRAM & X) ---
with st.sidebar:
    st.header("🔑 Anahtar Havuzu")
    if st.button("🔄 Test Et"):
        for k in api_keys:
            try:
                genai.configure(api_key=k)
                list(genai.list_models())
                st.markdown(f"🔑 ...{k[-4:]} ✅")
            except: st.markdown(f"🔑 ...{k[-4:]} ❌")
    
    st.markdown("---")
    st.header("📲 Telegram Köprüsü")
    tg_ticker = st.text_input("Kod (TG):", api_ticker_input, key="tg_ticker").upper()
    c1, c2 = st.columns(2)
    if c1.button("📉 Derinlik", key="t1"): st.session_state.tg_img_derinlik = fetch_data_via_bridge(tg_ticker, "derinlik")
    if c2.button("🏦 AKD", key="t2"): st.session_state.tg_img_akd = fetch_data_via_bridge(tg_ticker, "akd")
    c3, c4 = st.columns(2)
    if c3.button("📊 Kademe", key="t3"): st.session_state.tg_img_kademe = fetch_data_via_bridge(tg_ticker, "kademe")
    if c4.button("🌍 Takas", key="t4"): st.session_state.tg_img_takas = fetch_data_via_bridge(tg_ticker, "takas")
    
    st.markdown("---")
    st.header("𝕏 Tarayıcı")
    x_btn_url = f"https://x.com/search?q={quote(f'#{api_ticker_input} lang:tr')}&src=typed_query&f=live"
    st.markdown(f"""<a href="{x_btn_url}" target="_blank" class="x-btn">⏱️ Son Dakika</a>""", unsafe_allow_html=True)
    
    if st.button("🚪 Çıkış"):
        st.session_state.authenticated = False
        st.rerun()

# --- GÖRSEL YÖNETİMİ ---
file_key_suffix = str(st.session_state.reset_counter)
def render_panel(title, cat, tg_key, key_s):
    st.markdown(f"### {title}")
    if st.session_state[tg_key]:
        with st.container(border=True):
            st.image(st.session_state[tg_key], width=100)
            if st.button("🗑️", key=f"d_{cat}"): 
                st.session_state[tg_key] = None; st.rerun()
    
    st.file_uploader("Yükle", type=["jpg","png"], key=f"up_{key_s}", accept_multiple_files=True)
    
    if PASTE_ENABLED:
        res = paste_image_button(label="📋", key=f"p_{cat}_{key_s}")
        if res.image_data is not None:
             if not st.session_state[f"pasted_{cat}"] or st.session_state[f"pasted_{cat}"][-1] != res.image_data:
                st.session_state[f"pasted_{cat}"].append(res.image_data)
    
    if st.session_state[f"pasted_{cat}"]:
        cols = st.columns(3)
        for i, img in enumerate(st.session_state[f"pasted_{cat}"]):
            cols[i%3].image(img, use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    img_d_up = render_panel("1. Derinlik", "Derinlik", "tg_img_derinlik", f"d_{file_key_suffix}")
    st.markdown("---")
    img_k_up = render_panel("3. Kademe", "Kademe", "tg_img_kademe", f"k_{file_key_suffix}")
with c2:
    img_a_up = render_panel("2. AKD", "AKD", "tg_img_akd", f"a_{file_key_suffix}")
    st.markdown("---")
    img_t_up = render_panel("4. Takas", "Takas", "tg_img_takas", f"t_{file_key_suffix}")

# ==========================================
# 🧠 ANALİZ MODÜLÜ (FİNAL)
# ==========================================
st.markdown("---")
col_start, col_opts = st.columns([1, 2])

with col_start:
    st.markdown("<br>", unsafe_allow_html=True)
    start_btn = st.button("🐋 ANALİZİ BAŞLAT", type="primary", use_container_width=True)

with col_opts:
    analysis_mode = st.radio(
        "Analiz Modu:", 
        ("🚀 SADE MOD (Hızlı & Öz)", "🧠 GELİŞMİŞ MOD (Detaylı 50+)"),
        horizontal=True
    )
    if "GELİŞMİŞ" in analysis_mode:
        max_items = st.slider("Başlık Başına Madde", 15, 50, 20)
    else:
        max_items = 15

if start_btn:
    input_data = []
    context_str = ""
    
    # 1. API Data
    if st.session_state.api_depth_data:
        context_str += f"\n\n--- API DERİNLİK ---\n{json.dumps(st.session_state.api_depth_data, indent=2, ensure_ascii=False)}"
    if st.session_state.api_akd_data:
        context_str += f"\n\n--- API AKD ---\n{json.dumps(st.session_state.api_akd_data, indent=2, ensure_ascii=False)}"
    
    # 2. News
    if NEWS_ENABLED:
        with st.spinner("Haberler..."):
            context_str += f"\n\n--- HABERLER ---\n{fetch_stock_news(api_ticker_input)}"
    
    # 3. Images Helper
    def collect_images(up_key, paste_key, tg_key):
        imgs = []
        if st.session_state[f"up_{up_key}"]: 
            imgs.extend([compress_image(Image.open(f)) for f in st.session_state[f"up_{up_key}"]])
        if st.session_state[paste_key]: 
            imgs.extend([compress_image(i) for i in st.session_state[paste_key]])
        if st.session_state[tg_key]: 
            imgs.append(compress_image(st.session_state[tg_key]))
        if imgs: input_data.extend(imgs)
        return len(imgs) > 0

    has_d = collect_images(f"d_{file_key_suffix}", "pasted_Derinlik", "tg_img_derinlik")
    has_a = collect_images(f"a_{file_key_suffix}", "pasted_AKD", "tg_img_akd")
    has_k = collect_images(f"k_{file_key_suffix}", "pasted_Kademe", "tg_img_kademe")
    has_t = collect_images(f"t_{file_key_suffix}", "pasted_Takas", "tg_img_takas")

    # --- ŞABLON VE PROMPT ---
    show_depth = has_d or st.session_state.api_depth_data
    show_akd = has_a or st.session_state.api_akd_data
    show_kademe = has_k
    show_takas = has_t

    def build_template(advanced, count):
        tmpl = ""
        c = 1
        if show_depth:
            t = f"DETAYLI DERİNLİK (Min {count} Madde)" if advanced else "DERİNLİK ÖZETİ (Min 10 Madde)"
            tmpl += f"## {c}. 💹 {t}\n"; c+=1
        if show_akd:
            t = f"DETAYLI AKD (Min {count} Madde)" if advanced else "AKD ÖZETİ (Min 10 Madde)"
            tmpl += f"## {c}. 🤵 {t}\n"; c+=1
        if show_kademe:
            t = f"DETAYLI KADEME (Min {count} Madde)" if advanced else "KADEME ANALİZİ (Min 10 Madde)"
            tmpl += f"## {c}. 📊 {t}\n"; c+=1
        if show_takas:
            t = f"DETAYLI TAKAS (Min {count} Madde)" if advanced else "TAKAS ANALİZİ (Min 10 Madde)"
            tmpl += f"## {c}. 🌍 {t}\n"; c+=1
        
        if advanced:
            tmpl += f"## {c}. 🌡️ GENEL ALGI (Min {count} Madde)\n"; c+=1
            tmpl += f"## {c}. 🐋 GENEL SENTEZ (Min {count} Madde)\n"; c+=1
            tmpl += f"## {c}. 🚀 İŞLEM PLANI (Min {count} Madde)\n"
        else:
            tmpl += f"## {c}. 🛡️ DESTEK/DİRENÇ (Min 10 Adet)\n"; c+=1
            tmpl += f"## {c}. 🐋 BALİNA İZİ (Yorum)\n"; c+=1
            tmpl += f"## {c}. 🚀 İŞLEM PLANI (Strateji)\n"
        return tmpl

    is_adv = "GELİŞMİŞ" in analysis_mode
    final_template = build_template(is_adv, max_items)

    base_rules = """
    Sen Borsa Uzmanısın. Hissenin kodunu tespit et.
    
    🛑 FORMAT VE RENK KURALLARI (KESİN UYULACAK):
    1. ASLA PARAGRAF YAZMA. Sadece madde madde (Bullet points).
    2. RENK KURALI (HAYATİ ÖNEMDE): Cümlelerin içinde geçen kelimeleri veya tüm cümleyi duruma göre MUTLAKA renklendir.
       * Olumlu/Pozitif her şey için: :green[...] kullan.
       * Nötr/Bilgi verici her şey için: :blue[...] kullan.
       * Olumsuz/Negatif her şey için: :red[...] kullan.
       ÖRNEK: ":green[Alıcılar çok istekli] ancak :red[satış baskısı sürüyor]."
    3. SIRALAMA: Her başlık altında maddeleri şu sırayla yaz:
       * ÖNCE: ✅ :green[POZİTİF VERİLER]
       * SONRA: 🔵 :blue[NÖTR VERİLER]
       * EN SON: 🔻 :red[NEGATİF VERİLER]
    4. Verisi olmayan başlık uydurma.
    """

    if is_adv:
        prompt = f"""
        {base_rules}
        GÖREV: Aşağıdaki şablona göre EN İNCE AYRINTISINA KADAR analiz et.
        🛑 KURAL: Her başlık altına EN AZ {max_items} ADET madde yaz.
        
        --- VERİLER ---
        {context_str}
        
        --- ŞABLON ---
        {final_template}
        """
    else:
        prompt = f"""
        {base_rules}
        GÖREV: Aşağıdaki şablona göre analiz et.
        🛑 KURAL: Toplamda en az 20 madde olsun. Her başlığa en az 10 madde yaz.
        
        --- VERİLER ---
        {context_str}
        
        --- ŞABLON ---
        {final_template}
        """
    
    input_data.append(prompt)

    # --- ÇALIŞTIRMA ---
    if (not any([show_depth, show_akd, show_kademe, show_takas])) and not context_str:
        st.warning("⚠️ Yeterli veri yok!")
    else:
        placeholder = st.empty()
        full_res = ""
        with st.spinner("Analiz ediliyor..."):
            keys_local = api_keys.copy()
            if working_key in keys_local: 
                keys_local.remove(working_key); keys_local.insert(0, working_key)
            
            for k in keys_local:
                try:
                    genai.configure(api_key=k)
                    model = genai.GenerativeModel(valid_model_name)
                    stream = model.generate_content(input_data, stream=True)
                    st.session_state.active_working_key = k
                    working_key = k
                    for chunk in stream:
                        if chunk.text:
                            full_res += chunk.text
                            placeholder.markdown(full_res + "▌")
                    placeholder.markdown(full_res)
                    st.session_state.analysis_result = full_res
                    break
                except Exception as e:
                    if "429" not in str(e): st.error(f"Hata: {e}"); break

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
