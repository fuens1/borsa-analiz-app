import streamlit as st
from PIL import Image
import google.generativeai as genai
import datetime
import time
import io
from urllib.parse import quote

# Kopyala-Yapıştır Kütüphanesi Kontrolü
try:
    from streamlit_paste_button import paste_image_button
    PASTE_ENABLED = True
except ImportError:
    PASTE_ENABLED = False

# ==========================================
# 🔐 GÜVENLİK VE AYARLAR (BULUT VERSİYONU)
# ==========================================

st.set_page_config(page_title="BIST Yapay Zeka Analiz PRO", layout="wide", page_icon="🐋")

# Görsel stil ayarları
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    h1 { color: #00d4ff !important; }
    h2 { color: #ffbd45 !important; border-bottom: 2px solid #ffbd45; padding-bottom: 10px;}
    h3 { color: #00d4ff !important; }
    div[data-testid="stFileUploader"] { margin-bottom: 10px; }
    .stAlert { border-left: 5px solid #ffbd45; }
    
    /* Reset Butonu */
    div.stButton > button:first-child {
        font-weight: bold;
    }
    
    .x-btn {
        display: inline-block;
        background-color: #000000;
        color: white !important;
        padding: 12px 20px;
        text-align: center;
        text-decoration: none;
        font-size: 16px;
        border-radius: 8px;
        border: 1px solid #333;
        width: 100%;
        margin-top: 10px;
        transition: 0.3s;
    }
    .x-btn:hover {
        background-color: #1a1a1a;
        border-color: #1d9bf0;
        color: #1d9bf0 !important;
    }
    
    .key-status-pass { color: #00ff00; font-weight: bold; }
    .key-status-fail { color: #ff4444; font-weight: bold; }
    .key-status-limit { color: #ffbd45; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- ÜST BAR: BAŞLIK VE RESET BUTONU ---
col_title, col_reset = st.columns([5, 1])

with col_title:
    st.title("🐋 BIST Yapay Zeka Analiz PRO")
    st.info("Küçük Yatırımcının Büyüdüğü Bir Evren..")

with col_reset:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 SİSTEMİ SIFIRLA", type="secondary", help="Tüm verileri siler ve sayfayı yeniler."):
        # BUG FIX: Reset sayacını artırarak butonları zorla yeniliyoruz
        new_count = st.session_state.get("reset_counter", 0) + 1
        st.session_state.clear()
        st.session_state["reset_counter"] = new_count
        st.rerun()

# --- 1. API KEY HAVUZU YÖNETİMİ ---
api_keys = []

if "GOOGLE_API_KEY" in st.secrets:
    raw_secret = st.secrets["GOOGLE_API_KEY"]
    if "," in raw_secret:
        api_keys = [k.strip() for k in raw_secret.split(",") if k.strip()]
    else:
        api_keys = [raw_secret]

with st.sidebar:
    st.header("🔑 Anahtar Havuzu")

    # --- ANAHTAR TEST MODÜLÜ ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Durum Kontrolü")
    
    if st.sidebar.button("🔄 İstemci Verilerini Kontrol Et"):
        st.sidebar.info("Bağlantı kontrol ediliyor...")
        progress_bar = st.sidebar.progress(0)
        
        for i, key in enumerate(api_keys):
            try:
                genai.configure(api_key=key)
                models = list(genai.list_models())
                if not models: raise Exception("Liste boş")
                
                masked_key = f"{key[:4]}...{key[-4:]}"
                st.sidebar.markdown(f"🔑 `{masked_key}` : <span class='key-status-pass'>✅ AKTİF</span>", unsafe_allow_html=True)
                
            except Exception as e:
                masked_key = f"{key[:4]}...{key[-4:]}"
                err_msg = str(e)
                if "429" in err_msg or "quota" in err_msg.lower():
                    st.sidebar.markdown(f"🔑 `{masked_key}` : <span class='key-status-limit'>🛑 KOTA DOLU</span>", unsafe_allow_html=True)
                else:
                    st.sidebar.markdown(f"🔑 `{masked_key}` : <span class='key-status-fail'>❌ BAĞLANTI YOK</span>", unsafe_allow_html=True)
            
            progress_bar.progress((i + 1) / len(api_keys))
        st.sidebar.success("Kontrol Tamamlandı.")

# --- 2. BAŞLANGIÇ MODEL SEÇİMİ ---
valid_model_name = None
working_key = None

def get_model_name(key):
    try:
        genai.configure(api_key=key)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in models:
            if "gemini-1.5-flash" in m and "002" in m: return m
        for m in models:
            if "gemini-1.5-flash" in m and "latest" not in m: return m
        for m in models:
            if "gemini-1.5-flash" in m: return m
        return models[0] if models else None
    except:
        return None

for k in api_keys:
    mod = get_model_name(k)
    if mod:
        valid_model_name = mod
        working_key = k
        break

if not valid_model_name:
    st.error("❌ Hiçbir anahtar ile modele bağlanılamadı.")
    st.stop()

# --- 3. FAILOVER İSTEK FONKSİYONU ---
def make_resilient_request(content_input, keys_list):
    last_error = None
    if working_key in keys_list:
        keys_list.remove(working_key)
        keys_list.insert(0, working_key)
        
    for index, key in enumerate(keys_list):
        try:
            genai.configure(api_key=key)
            model_instance = genai.GenerativeModel(valid_model_name)
            response = model_instance.generate_content(content_input)
            st.session_state.active_working_key = key
            return response.text
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "resource" in err_str.lower():
                print(f"Anahtar {index+1} kotası doldu. Sıradakine geçiliyor...")
                continue
            else:
                last_error = e
                break
    
    if last_error: raise last_error
    else: raise Exception("Tüm anahtarların kotası dolu! Biraz bekleyin.")

# --- SESSION STATE ---
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "loaded_count" not in st.session_state:
    st.session_state.loaded_count = 0
if "active_working_key" not in st.session_state:
    st.session_state.active_working_key = working_key
if "reset_counter" not in st.session_state:
    st.session_state.reset_counter = 0

# Paste hafızası
for cat in ["Derinlik", "AKD", "Kademe", "Takas"]:
    if f"pasted_{cat}" not in st.session_state:
        st.session_state[f"pasted_{cat}"] = []

# ==========================================
# 🐦 YAN MENÜ: X (TWITTER) TARAYICI
# ==========================================
with st.sidebar:
    st.markdown("---")
    st.header("𝕏 (#Hashtag) Tarayıcı")
    
    # --- YENİ EKLENEN POPÜLER HİSSE LİSTESİ ---
    bist_30 = [
        "THYAO", "ASELS", "EREGL", "KCHOL", "ISCTR", "AKBNK", "YKBNK", "SAHOL", "TUPRS", "SISE",
        "PETKM", "BIMAS", "HEKTS", "SASA", "KONTR", "EKGYO", "ODAS", "KOZAL", "KRDMD", "GARAN",
        "TCELL", "FROTO", "ENKAI", "GUBRF", "VESTL", "TOASO", "PGSUS", "ARCLK", "ALARK", "ASTOR"
    ]
    
    st.subheader("🔥 İLK 10 POPÜLER (BIST 30)")
    # Kullanıcı listeden seçerse raw_ticker otomatik dolar
    selected_stock = st.selectbox(
        "Hızlı Erişim Listesi:", 
        ["Manuel Giriş Yap"] + bist_30,
        index=0
    )
    
    if selected_stock != "Manuel Giriş Yap":
        raw_ticker = selected_stock
        st.caption(f"✅ **{selected_stock}** seçildi.")
    else:
        raw_ticker = st.text_input("Hisse Kodu (Örn: REEDR)", "THYAO").upper()

    clean_ticker = raw_ticker.replace("#", "").replace("$", "").strip()
    
    st.markdown("---")
    st.caption("💬 Gündemi Takip Et 💬")
    
    search_mode = st.radio("Arama Tipi:", ("🔥 En Popüler (Geçmiş)", "⏱️ Son Dakika (Canlı)"))
    
    x_url = ""
    btn_text = ""
    
    if search_mode == "🔥 En Popüler (Geçmiş)":
        selected_date = st.date_input("Hangi Tarih?", datetime.date.today())
        next_day = selected_date + datetime.timedelta(days=1)
        search_query = f"#{clean_ticker} lang:tr until:{next_day} since:{selected_date} min_faves:5"
        encoded_query = quote(search_query)
        x_url = f"https://x.com/search?q={encoded_query}&src=typed_query&f=top"
        btn_text = f"🔥 <b>{selected_date}</b> Tarihli<br>Popüler <b>#{clean_ticker}</b> Tweetleri"
    else: 
        search_query = f"#{clean_ticker} lang:tr"
        encoded_query = quote(search_query)
        x_url = f"https://x.com/search?q={encoded_query}&src=typed_query&f=live"
        btn_text = f"⏱️ <b>#{clean_ticker}</b> Hakkında<br>Son Dakika Akışını Gör"

    st.markdown(f"""<a href="{x_url}" target="_blank" class="x-btn">{btn_text}</a>""", unsafe_allow_html=True)

# ==========================================
# 📤 YÜKLEME VE YAPIŞTIRMA ALANLARI
# ==========================================

# Yardımcı Fonksiyon: Yapıştırılan Resmi Ekle
def handle_paste(category):
    if PASTE_ENABLED:
        # Key'e reset_counter ekleyerek cache'i kırıyoruz
        unique_key = f"btn_paste_{category}_{st.session_state.reset_counter}"
        paste_result = paste_image_button(
            label=f"📋 Panodan Yapıştır ({category})",
            background_color="#1E2130",
            hover_background_color="#333",
            key=unique_key
        )
        if paste_result.image_data is not None:
            img = paste_result.image_data
            if len(st.session_state[f"pasted_{category}"]) == 0 or \
               st.session_state[f"pasted_{category}"][-1] != img:
                st.session_state[f"pasted_{category}"].append(img)
    else:
        st.warning(f"Yapıştırma özelliği için: `pip install streamlit-paste-button`")

# Yardımcı Fonksiyon: Yapıştırılanları Göster
def show_pasted_images(category):
    if st.session_state[f"pasted_{category}"]:
        st.caption(f"📌 Panodan Eklenenler ({len(st.session_state[f'pasted_{category}'])}):")
        cols = st.columns(3)
        for i, img in enumerate(st.session_state[f"pasted_{category}"]):
            with cols[i % 3]:
                st.image(img, width=100)

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 1. Derinlik Ekranı 💹")
    img_derinlik_list = st.file_uploader("Derinlik Görüntüsü 💹", type=["jpg", "png", "jpeg"], key="d", accept_multiple_files=True)
    handle_paste("Derinlik")
    show_pasted_images("Derinlik")
    
    st.markdown("---")
    
    st.markdown("### 3. Kademe Analizi 📊")
    img_kademe_list = st.file_uploader("Kademe Analiz Ekranı 📊", type=["jpg", "png", "jpeg"], key="e", accept_multiple_files=True)
    handle_paste("Kademe")
    show_pasted_images("Kademe")

with col2:
    st.markdown("### 2. AKD (Aracı Kurum) 🤵")
    img_akd_list = st.file_uploader("AKD Ekranı 🤵", type=["jpg", "png", "jpeg"], key="a", accept_multiple_files=True)
    handle_paste("AKD")
    show_pasted_images("AKD")
    
    st.markdown("---")
    
    st.markdown("### 4. Takas Analizi 🌍")
    img_takas_list = st.file_uploader("Takas Ekranı 🌍", type=["jpg", "png", "jpeg"], key="t", accept_multiple_files=True)
    handle_paste("Takas")
    show_pasted_images("Takas")

# ==========================================
# 🚀 ANALİZ MOTORU & HIZ KONTROLÜ
# ==========================================
st.markdown("---")

col_btn, col_settings = st.columns([1, 1])

with col_settings:
    is_summary_mode = st.toggle("⚡ KISA ÖZET MODU", value=False, help="Aktif edilirse analiz çok hızlı biter, detaylar atlanır.")
    if not is_summary_mode:
        max_items = st.slider("Maksimum Analiz Maddesi:", min_value=5, max_value=30, value=20)
    else:
        max_items = 5

with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("🐋 ANALİZİ BAŞLAT", type="primary", use_container_width=True)

if analyze_btn:
    
    st.session_state.messages = [] 
    input_content = []
    
    # --- DİNAMİK BAŞLIK OLUŞTURUCU ---
    # Hem yüklenen hem yapıştırılanları kontrol et
    has_derinlik = bool(img_derinlik_list) or bool(st.session_state["pasted_Derinlik"])
    has_akd = bool(img_akd_list) or bool(st.session_state["pasted_AKD"])
    has_kademe = bool(img_kademe_list) or bool(st.session_state["pasted_Kademe"])
    has_takas = bool(img_takas_list) or bool(st.session_state["pasted_Takas"])
    
    dynamic_sections_prompt = ""
    
    if is_summary_mode:
        if has_derinlik: dynamic_sections_prompt += "## 💹 DERİNLİK ÖZETİ (En Kritik 3-5 Nokta)\n"
        if has_akd: dynamic_sections_prompt += "## 🤵 AKD ÖZETİ (Para Giriş/Çıkış)\n"
        if has_kademe: dynamic_sections_prompt += "## 📊 KADEME ÖZETİ (Güçlü Alıcı/Satıcı)\n"
        if has_takas: dynamic_sections_prompt += "## 🌍 TAKAS ÖZETİ (Yabancı Durumu)\n"
    else:
        if has_derinlik: 
            dynamic_sections_prompt += f"""
            ## 📸 DERİNLİK ANALİZİ (Maks {max_items} Madde)
            (Pozitif > Nötr > Negatif Gruplu Formatı Uygula)
            """
        if has_akd:
            dynamic_sections_prompt += f"""
            ## 🏦 AKD (ARACI KURUM) ANALİZİ (Maks {max_items} Madde)
            (Pozitif > Nötr > Negatif Gruplu Formatı Uygula)
            """
        if has_kademe:
            dynamic_sections_prompt += f"""
            ## 📊 KADEME & HACİM ANALİZİ (Maks {max_items} Madde)
            (Alt Başlıklar: Kurumsal Alış, Kurumsal Satış, Bireysel Davranış, POC)
            """
        if has_takas:
            dynamic_sections_prompt += f"""
            ## 🌍 TAKAS ANALİZİ (Maks {max_items} Madde)
            (Pozitif > Nötr > Negatif Gruplu Formatı Uygula)
            """

    # --- ANA PROMPT ---
    base_prompt = f"""
    Sen Borsa İstanbul Uzmanısın.
    GÖREV: Yüklenen görselleri analiz et.
    
    🚨 İLK İŞİN: Görselden hisse adını tespit et. Yoksa "HEDEF HİSSE" de.
    🚨 KURAL: Sadece aşağıda başlığı verilen bölümleri rapora ekle. Yüklenmeyen veriler için başlık açma.
    
    --- İSTENEN RAPOR FORMATI ---
    
    {dynamic_sections_prompt}
    
    --- ORTAK KAPANIŞ BÖLÜMÜ (HER ZAMAN EKLE) ---
    
    ## 🐋 GENEL SENTEZ (BALİNA İZİ)
    BU BÖLÜMÜ PARAGRAF ŞEKLİNDE YAZMA. AŞAĞIDAKİ GİBİ MADDE MADDE SIRALA:
    
    **🟢 POZİTİF / OLUMLU SENTEZ:**
    1. [Balina izi madde 1]
    2. [Balina izi madde 2]
    
    **🔵 BİLGİ / NÖTR SENTEZ:**
    1. [Bilgi madde 1]
    
    **🔴 NEGATİF / RİSKLİ SENTEZ:**
    1. [Riskli durum madde 1]
    2. [Riskli durum madde 2]

    ## 💯 SKOR KARTI & TRENDMETRE (DETAYLI)
    **GENEL SKOR:** [0-100
