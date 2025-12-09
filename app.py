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
from urllib.parse import quote

# Paste Button Check
try:
    from streamlit_paste_button import paste_image_button
    PASTE_ENABLED = True
except ImportError:
    PASTE_ENABLED = False

# ==========================================
# 🔐 GLOBAL AYAR YÖNETİMİ
# ==========================================
CONFIG_FILE = "site_config.json"

def load_global_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {"beta_active": True}
    return {"beta_active": True}

def save_global_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

global_config = load_global_config()

# ==========================================
# 🎨 SAYFA AYARLARI
# ==========================================

st.set_page_config(page_title="BIST Yapay Zeka Analiz PRO", layout="wide", page_icon="🐋")

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
    st.title("🐋 BIST Yapay Zeka Analiz PRO")
    if st.session_state.is_admin: st.success("👑 YÖNETİCİ MODU")
    else: st.info("Küçük Yatırımcının Büyüdüğü Bir Evren..")

with col_reset:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 SİSTEMİ SIFIRLA", type="secondary"):
        st.session_state.reset_counter += 1
        st.session_state.api_depth_data = None
        st.session_state.api_akd_data = None
        
        keys_to_keep = ["authenticated", "is_admin", "reset_counter", "api_depth_data", "api_akd_data"]
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
    fetch_btn = st.button("TÜM VERİLERİ GETİR", type="primary")

if fetch_btn:
    # 1. HissePlus API (Canlı Veri)
    try:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        with st.spinner(f"{api_ticker_input} Canlı Verileri Çekiliyor..."):
            url_depth = f"https://webapi.hisseplus.com/api/v1/kademe?sembol={api_ticker_input}"
            r_depth = requests.get(url_depth, headers=headers)
            st.session_state.api_depth_data = r_depth.json() if r_depth.status_code == 200 else None
            
            url_akd = f"https://webapi.hisseplus.com/api/v1/akd?sembol={api_ticker_input}&ilk={today_str}&son={today_str}"
            r_akd = requests.get(url_akd, headers=headers)
            st.session_state.api_akd_data = r_akd.json() if r_akd.status_code == 200 else None
    except Exception as e:
        st.error(f"API Hatası: {e}")

# --- DATA PREVIEW TABS ---
if st.session_state.api_depth_data or st.session_state.api_akd_data:
    with st.expander("📊 Toplanan Verileri İncele", expanded=True):
        tab1, tab2 = st.tabs(["📉 Canlı Tahta", "🔍 Ham Veri"])
        
        with tab1:
            c1, c2 = st.columns(2)
            with c1: 
                st.markdown("**Derinlik**")
                if st.session_state.api_depth_data:
                    try:
                        df = pd.DataFrame(st.session_state.api_depth_data.get('data', []))
                        st.dataframe(df, use_container_width=True, height=200)
                    except: st.json(st.session_state.api_depth_data)
            with c2:
                st.markdown("**AKD**")
                if st.session_state.api_akd_data:
                    try:
                        df = pd.DataFrame(st.session_state.api_akd_data.get('data', []))
                        st.dataframe(df, use_container_width=True, height=200)
                    except: st.json(st.session_state.api_akd_data)
        
        with tab2:
            st.json(st.session_state.api_depth_data)

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

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔑 Anahtar Havuzu")
    if st.button("🔄 Anahtarları Test Et"):
        prog = st.progress(0)
        for i, k in enumerate(api_keys):
            try:
                genai.configure(api_key=k)
                list(genai.list_models())
                st.markdown(f"🔑 `...{k[-4:]}` : <span class='key-status-pass'>✅</span>", unsafe_allow_html=True)
            except: st.markdown(f"🔑 `...{k[-4:]}` : <span class='key-status-fail'>❌</span>", unsafe_allow_html=True)
            prog.progress((i+1)/len(api_keys))
    
    st.markdown("---")
    if st.button("🚪 Çıkış Yap"):
        st.session_state.authenticated = False
        st.rerun()

    if st.session_state.is_admin:
        st.subheader("⚙️ Yönetici")
        curr = global_config["beta_active"]
        new_s = st.toggle("Beta Açık", value=curr)
        if new_s != curr:
            global_config["beta_active"] = new_s
            save_global_config(global_config)
            st.rerun()
        if not new_s: st.caption("🔴 Beta Kapalı.")
        else: st.caption("🟢 Beta Açık.")

with st.sidebar:
    st.markdown("---")
    st.header("𝕏 Tarayıcı")
    raw_ticker = st.text_input("Kod:", api_ticker_input).upper() # Yukarıdaki inputla senkronize
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
            if "gemini-1.5-flash" in m and "002" in m: return m
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

def make_resilient_request(content, keys):
    global working_key
    local_keys = keys.copy()
    if working_key in local_keys:
        local_keys.remove(working_key)
        local_keys.insert(0, working_key)
    for k in local_keys:
        try:
            genai.configure(api_key=k)
            model = genai.GenerativeModel(valid_model_name)
            resp = model.generate_content(content)
            st.session_state.active_working_key = k
            working_key = k
            return resp.text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower(): continue
            else: raise e
    raise Exception("Tüm kotalar dolu.")

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
        cols = st.columns(3)
        for i, img in enumerate(st.session_state[f"pasted_{cat}"]):
            cols[i%3].image(img, width=100)

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 1. Derinlik 💹")
    img_d = st.file_uploader("Yükle", type=["jpg","png","jpeg"], key=f"d_{file_key_suffix}", accept_multiple_files=True)
    handle_paste("Derinlik")
    show_images("Derinlik")
    st.markdown("### 3. Kademe 📊")
    img_k = st.file_uploader("Yükle", type=["jpg","png","jpeg"], key=f"k_{file_key_suffix}", accept_multiple_files=True)
    handle_paste("Kademe")
    show_images("Kademe")

with col2:
    st.markdown("### 2. AKD 🤵")
    img_a = st.file_uploader("Yükle", type=["jpg","png","jpeg"], key=f"a_{file_key_suffix}", accept_multiple_files=True)
    handle_paste("AKD")
    show_images("AKD")
    st.markdown("### 4. Takas 🌍")
    img_t = st.file_uploader("Yükle", type=["jpg","png","jpeg"], key=f"t_{file_key_suffix}", accept_multiple_files=True)
    handle_paste("Takas")
    show_images("Takas")

# --- ANALYZE ---
st.markdown("---")
c1, c2 = st.columns([1, 1])
with c2:
    is_summary = st.toggle("⚡ KISA ÖZET", value=False)
    max_items = 5 if is_summary else st.slider("Madde Limiti", 5, 30, 20)

with c1:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🐋 ANALİZİ BAŞLAT", type="primary", use_container_width=True):
        input_data = []
        
        # --- BİRLEŞTİRİLMİŞ VERİ SETİ ---
        context_str = ""
        # 1. API
        if st.session_state.api_depth_data:
            context_str += f"\n\n--- CANLI DERİNLİK API VERİSİ (HissePlus) ---\n{json.dumps(st.session_state.api_depth_data, indent=2, ensure_ascii=False)}"
        if st.session_state.api_akd_data:
            context_str += f"\n\n--- CANLI AKD API VERİSİ (HissePlus) ---\n{json.dumps(st.session_state.api_akd_data, indent=2, ensure_ascii=False)}"

        has_d = bool(img_d) or bool(st.session_state["pasted_Derinlik"]) or bool(st.session_state.api_depth_data)
        has_a = bool(img_a) or bool(st.session_state["pasted_AKD"]) or bool(st.session_state.api_akd_data)
        has_k = bool(img_k) or bool(st.session_state["pasted_Kademe"])
        has_t = bool(img_t) or bool(st.session_state["pasted_Takas"])
        
        sections = ""
        if is_summary:
            if has_d: sections += "## 💹 DERİNLİK ÖZETİ (3-5 Madde)\n"
            if has_a: sections += "## 🤵 AKD ÖZETİ\n"
            if has_k: sections += "## 📊 KADEME ÖZETİ\n"
            if has_t: sections += "## 🌍 TAKAS ÖZETİ\n"
        else:
            if has_d: sections += f"## 📸 DERİNLİK ANALİZİ (Maks {max_items}, Pozitif/Nötr/Negatif Gruplu, Renkli)\n"
            if has_a: sections += f"## 🏦 AKD ANALİZİ (Maks {max_items}, Pozitif/Nötr/Negatif Gruplu, Renkli)\n"
            if has_k: sections += f"## 📊 KADEME ANALİZİ (Maks {max_items}, Alt Başlıklar)\n"
            if has_t: sections += f"## 🌍 TAKAS ANALİZİ (Maks {max_items}, Gruplu, Renkli)\n"

        prompt = f"""
        Sen Borsa Uzmanısın. GÖREV: Verilen Görselleri, CANLI API VERİLERİNİ ve HABERLERİ analiz et.
        🚨 Hisse kodunu görselden veya veriden bul.
        
        ÖNEMLİ FORMAT KURALLARI:
        1. Başlıkları madde madde listele. ASLA paragraf yapma.
        2. Renkleri kullan: :green[], :blue[], :red[].
        3. Genel Sentez kısmını PARAGRAF olarak yaz.
        4. Trendmetre kısmını TABLO olarak yap.
        
        --- MEVCUT VERİ SETİ ---
        {context_str}
        
        --- İSTENEN RAPOR FORMATI ---
        {sections}
        
        --- ÖZEL BÖLÜM (MADDE SINIRI YOK) ---
        ## 🛡️ GÜÇLÜ/ZAYIF DESTEK VE DİRENÇ ANALİZİ
        (Madde sınırı yok. Tüm seviyeleri yaz.)
        * Destekler :green[YEŞİL], Dirençler :red[KIRMIZI]
        * Yorumlar: "Bu direnç kırılırsa tavana (9.90) gidebilir" gibi stratejik ve net olsun.
        
        ## 🧭 YÖN / FİYAT OLASILIĞI VE SENARYOLAR (DETAYLI)
        (Eldeki Derinlik, AKD ve Takas verilerine dayanarak matematiksel bir projeksiyon yap.)
        * **📈 Yükseliş İhtimali:** % [Oran]
        * **📉 Düşüş İhtimali:** % [Oran]
        * **➖ Yatay Seyir İhtimali:** % [Oran]

        **Senaryolar ve Hedefler:**
        1. **Yukarı Yönlü Hareket:** Eğer fiyat [X] seviyesini aşarsa, [Y] fiyatına gitme potansiyeli var. (Neden: ...)
        2. **Aşağı Yönlü Hareket:** Eğer fiyat [A] desteğini kırarsa, [B] fiyatına çekilebilir. (Neden: ...)
        3. **En Kritik Kırılım Noktası:** [Fiyat]
        
        --- GENEL (HER ZAMAN) ---
        ## 🌡️ PİYASA DUYGU ÖLÇER (SEKTÖREL SENTIMENT)
        (Analizi yapılan hissenin ait olduğu sektöre göre yatırımcı ilgisini puanla: 0=Sektöre İlgi Yok, 100=Sektörde İlgi Çok Fazla. Sebebini yaz.)
        
        ## 🐋 GENEL SENTEZ (BALİNA İZİ) (Paragraf)
        ## 💯 SKOR KARTI & TRENDMETRE (Tablo)
        ## 🚀 İŞLEM PLANI
        """
        
        input_data.append(prompt)
        
        def add_imgs(fl, pl):
            if fl: [input_data.append(Image.open(f)) for f in fl]
            if pl: [input_data.append(i) for i in pl]
            return bool(fl or pl)

        count = 0
        if add_imgs(img_d, st.session_state["pasted_Derinlik"]): input_data.append("\nDERİNLİK GÖRSELİ\n"); count+=1
        if add_imgs(img_a, st.session_state["pasted_AKD"]): input_data.append("\nAKD GÖRSELİ\n"); count+=1
        if add_imgs(img_k, st.session_state["pasted_Kademe"]): input_data.append("\nKADEME GÖRSELİ\n"); count+=1
        if add_imgs(img_t, st.session_state["pasted_Takas"]): input_data.append("\nTAKAS GÖRSELİ\n"); count+=1
        
        if count == 0 and not context_str:
            st.warning("⚠️ Lütfen analiz için veri yükleyin (Görsel veya 'TÜM VERİLERİ GETİR' butonu).")
        else:
            with st.spinner("Analiz yapılıyor... (Teknik Veriler harmanlanıyor)"):
                try:
                    res = make_resilient_request(input_data, api_keys)
                    st.session_state.analysis_result = res
                    st.session_state.loaded_count = count
                    st.rerun()
                except Exception as e:
                    st.error(f"HATA: {e}")

# --- RESULT ---
if st.session_state.analysis_result:
    st.markdown("## 🐋 Kurumsal Rapor")
    st.markdown(st.session_state.analysis_result)
    st.markdown("---")
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    if q := st.chat_input("Sorunuz..."):
        st.session_state.messages.append({"role":"user", "content":q})
        with st.chat_message("user"): st.markdown(q)
        
        with st.chat_message("assistant"):
            try:
                genai.configure(api_key=st.session_state.active_working_key)
                model = genai.GenerativeModel(valid_model_name)
                stream = model.generate_content(f"Context: {st.session_state.analysis_result}\nUser: {q}", stream=True)
                def parser():
                    for ch in stream: 
                        if ch.text: yield ch.text
                resp = st.write_stream(parser)
                st.session_state.messages.append({"role":"assistant", "content":resp})
            except: st.error("Hata.")
