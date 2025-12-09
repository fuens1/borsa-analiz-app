import streamlit as st
from PIL import Image
import google.generativeai as genai
import datetime
import time
import io
from urllib.parse import quote

# Paste Button Check
try:
    from streamlit_paste_button import paste_image_button
    PASTE_ENABLED = True
except ImportError:
    PASTE_ENABLED = False

# ==========================================
# 🔐 CONFIG & STYLING
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
    .key-status-pass { color: #00ff00; font-weight: bold; }
    .key-status-fail { color: #ff4444; font-weight: bold; }
    .key-status-limit { color: #ffbd45; font-weight: bold; }
    .login-box {
        border: 2px solid #00d4ff; padding: 40px; border-radius: 15px;
        background-color: #1E2130; text-align: center; margin-top: 50px;
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION INIT ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "is_admin" not in st.session_state: st.session_state.is_admin = False
if "reset_counter" not in st.session_state: st.session_state.reset_counter = 0
# Beta Mode Default (Bunu veritabanı olmadığı için session'da tutuyoruz, kalıcı olması için Secrets'a yazman lazım)
if "beta_active" not in st.session_state: st.session_state.beta_active = True 

# --- AUTH & ADMIN LOGIC ---
query_params = st.query_params
admin_secret = st.secrets.get("ADMIN_KEY", "admin123") 

# Admin Link Check (?admin=KEY)
if query_params.get("admin") == admin_secret:
    st.session_state.authenticated = True
    st.session_state.is_admin = True

def check_password():
    if "APP_PASSWORD" in st.secrets:
        correct_password = st.secrets["APP_PASSWORD"]
    else:
        st.error("🚨 Secrets Hatası: APP_PASSWORD eksik.")
        st.stop()

    input_pass = st.session_state.get("password_input", "")
    
    if input_pass == correct_password:
        if st.session_state.beta_active:
            st.session_state.authenticated = True
            st.session_state.is_admin = False # Normal user
        else:
            st.error("🚧 Sistem şu an bakımda. Sadece Admin girebilir.")
    elif input_pass == admin_secret: # Admin şifreyi kutuya yazarsa da girsin
        st.session_state.authenticated = True
        st.session_state.is_admin = True
    elif input_pass:
        st.error("❌ Hatalı Giriş Kodu!")

# --- LOGIN SCREEN ---
if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.title("🔒 Beta Erişim Kapısı")
        
        if st.session_state.beta_active:
            st.info("Davetiye kodunuzu giriniz.")
            st.text_input("Giriş Kodu:", type="password", key="password_input", on_change=check_password)
            if st.button("Giriş Yap"): check_password()
        else:
            st.warning("⚠️ BETA GİRİŞLERİ GEÇİCİ OLARAK KAPALIDIR.")
            # Admin için gizli giriş imkanı bırakalım
            st.text_input("Admin Girişi:", type="password", key="password_input", on_change=check_password)
            if st.button("Yönetici Girişi"): check_password()
            
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop() 

# ==========================================
# 🚀 MAIN APP
# ==========================================

# --- RESET LOGIC ---
col_title, col_reset = st.columns([5, 1])
with col_title:
    st.title("🐋 BIST Yapay Zeka Analiz PRO")
    if st.session_state.is_admin:
        st.caption("👑 YÖNETİCİ MODU AKTİF")
    else:
        st.info("Küçük Yatırımcının Büyüdüğü Bir Evren..")

with col_reset:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 SİSTEMİ SIFIRLA", type="secondary", help="Tüm verileri siler."):
        # Increment counter to force-clear file uploaders
        st.session_state.reset_counter += 1
        
        # Clear specific session keys but keep auth & settings
        keys_to_keep = ["authenticated", "is_admin", "reset_counter", "beta_active"]
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep:
                del st.session_state[key]
        
        # Init paste buffers
        for cat in ["Derinlik", "AKD", "Kademe", "Takas"]:
            st.session_state[f"pasted_{cat}"] = []
            
        st.rerun()

# --- INIT VARIABLES ---
api_keys = []
if "GOOGLE_API_KEY" in st.secrets:
    raw = st.secrets["GOOGLE_API_KEY"]
    api_keys = [k.strip() for k in raw.split(",") if k.strip()] if "," in raw else [raw]

if "analysis_result" not in st.session_state: st.session_state.analysis_result = None
if "messages" not in st.session_state: st.session_state.messages = []
if "loaded_count" not in st.session_state: st.session_state.loaded_count = 0
if "active_working_key" not in st.session_state: st.session_state.active_working_key = None

# Init paste buffers if not exists
for cat in ["Derinlik", "AKD", "Kademe", "Takas"]:
    if f"pasted_{cat}" not in st.session_state: st.session_state[f"pasted_{cat}"] = []

# --- SIDEBAR: KEY MANAGEMENT ---
with st.sidebar:
    st.header("🔑 Anahtar Havuzu")
    
    if st.button("🔄 Anahtarları Test Et"):
        st.info("Kontrol ediliyor...")
        prog = st.progress(0)
        for i, k in enumerate(api_keys):
            try:
                genai.configure(api_key=k)
                list(genai.list_models())
                st.markdown(f"🔑 `...{k[-4:]}` : <span class='key-status-pass'>✅ AKTİF</span>", unsafe_allow_html=True)
            except Exception as e:
                if "429" in str(e): st.markdown(f"🔑 `...{k[-4:]}` : <span class='key-status-limit'>🛑 KOTA</span>", unsafe_allow_html=True)
                else: st.markdown(f"🔑 `...{k[-4:]}` : <span class='key-status-fail'>❌ HATA</span>", unsafe_allow_html=True)
            prog.progress((i+1)/len(api_keys))
    
    st.markdown("---")
    if st.button("🚪 Çıkış Yap"):
        st.session_state.authenticated = False
        st.rerun()

    # --- ADMIN PANEL (Sadece Admin Görür) ---
    if st.session_state.is_admin:
        st.markdown("---")
        st.subheader("⚙️ Yönetici Paneli")
        
        # Beta Switch
        beta_status = st.toggle("Beta Girişlerini Aç", value=st.session_state.beta_active)
        if beta_status != st.session_state.beta_active:
            st.session_state.beta_active = beta_status
            if beta_status: st.success("Beta Açıldı!")
            else: st.error("Beta Kapatıldı! Sadece Admin girebilir.")

# --- X BROWSER ---
with st.sidebar:
    st.markdown("---")
    st.header("𝕏 (#Hashtag) Tarayıcı")
    raw_ticker = st.text_input("Hisse Kodu (Örn: THYAO)", "THYAO").upper()
    clean_ticker = raw_ticker.replace("#", "").replace("$", "").strip()
    
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

def make_request(content, keys):
    if working_key in keys:
        keys.remove(working_key)
        keys.insert(0, working_key)
    for k in keys:
        try:
            genai.configure(api_key=k)
            model = genai.GenerativeModel(valid_model_name)
            resp = model.generate_content(content)
            st.session_state.active_working_key = k
            return resp.text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower(): continue
            else: raise e
    raise Exception("Tüm kotalar dolu.")

# --- UPLOAD SECTION ---
# Key'e reset_counter ekleyerek zorla yeniliyoruz (Dosyaları siler)
file_key_suffix = str(st.session_state.reset_counter)

def handle_paste(cat):
    if PASTE_ENABLED:
        res = paste_image_button(
            label=f"📋 Yapıştır", 
            background_color="#1E2130", hover_background_color="#333",
            key=f"paste_{cat}_{file_key_suffix}" # Resetlenince ID değişir, hafıza silinir
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
        
        # Dynamic Prompt Logic
        has_d = bool(img_d) or bool(st.session_state["pasted_Derinlik"])
        has_a = bool(img_a) or bool(st.session_state["pasted_AKD"])
        has_k = bool(img_k) or bool(st.session_state["pasted_Kademe"])
        has_t = bool(img_t) or bool(st.session_state["pasted_Takas"])
        
        sections = ""
        if is_summary:
            if has_d: sections += "## 💹 DERİNLİK ÖZETİ (3-5 Madde)\n"
            if has_a: sections += "## 🤵 AKD ÖZETİ\n"
            if has_k: sections += "## 📊 KADEME ÖZETİ\n"
            if has_t: sections += "## 🌍 TAKAS ÖZETİ\n"
        else:
            if has_d: sections += f"## 📸 DERİNLİK ANALİZİ (Maks {max_items}, Pozitif/Nötr/Negatif Gruplu)\n"
            if has_a: sections += f"## 🏦 AKD ANALİZİ (Maks {max_items}, Pozitif/Nötr/Negatif Gruplu)\n"
            if has_k: sections += f"## 📊 KADEME ANALİZİ (Maks {max_items}, Alt Başlıklar)\n"
            if has_t: sections += f"## 🌍 TAKAS ANALİZİ (Maks {max_items}, Gruplu)\n"

        prompt = f"""
        Sen Borsa Uzmanısın. GÖREV: Görselleri analiz et.
        🚨 Hisse kodunu görselden bul.
        --- FORMAT ---
        {sections}
        --- GENEL (HER ZAMAN) ---
        ## 🐋 GENEL SENTEZ (BALİNA İZİ) (Paragraf)
        ## 💯 SKOR KARTI & TRENDMETRE (Tablo)
        ## 🔮 GÜN SONU TAHMİNİ (% Olasılıklar ve Nedenleri)
        ## 🚀 İŞLEM PLANI
        """
        
        input_data.append(prompt)
        
        def add_imgs(fl, pl):
            if fl: [input_data.append(Image.open(f)) for f in fl]
            if pl: [input_data.append(i) for i in pl]
            return bool(fl or pl)

        count = 0
        if add_imgs(img_d, st.session_state["pasted_Derinlik"]): input_data.append("\nDERİNLİK\n"); count+=1
        if add_imgs(img_a, st.session_state["pasted_AKD"]): input_data.append("\nAKD\n"); count+=1
        if add_imgs(img_k, st.session_state["pasted_Kademe"]): input_data.append("\nKADEME\n"); count+=1
        if add_imgs(img_t, st.session_state["pasted_Takas"]): input_data.append("\nTAKAS\n"); count+=1
        
        if count == 0:
            st.warning("⚠️ Görsel yükleyiniz.")
        else:
            with st.spinner("Analiz yapılıyor..."):
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
    
    # Chat
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
                resp = st.write_stream(chunk.text for chunk in stream if chunk.text)
                st.session_state.messages.append({"role":"assistant", "content":resp})
            except: st.error("Hata.")
