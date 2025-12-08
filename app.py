import streamlit as st
from PIL import Image
import google.generativeai as genai
import os

# ==========================================
# 🔐 GÜVENLİK VE AYARLAR (BULUT VERSİYONU)
# ==========================================

st.set_page_config(page_title="BIST Analiz Pro V4", layout="wide", page_icon="📈")

# Görsel stil ayarları
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    h1 { color: #00d4ff !important; }
    h3 { color: #ffbd45 !important; }
    div[data-testid="stFileUploader"] { margin-bottom: 20px; }
    .stAlert { border-left: 5px solid #ffbd45; }
</style>
""", unsafe_allow_html=True)

st.title("📈 BIST Profesyonel Analiz Masası (Cloud)")
st.info("Bu uygulama 7/24 Bulut Sunucuda çalışmaktadır. Görsellerinizi yükleyin ve analizi başlatın.")

# --- API KEY KONTROLÜ (SECRETS) ---
# Önce Bulut Kasasına (st.secrets) bakar, yoksa Sidebar'dan ister.
api_key = None

if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    with st.sidebar:
        st.warning("⚠️ API Key Bulunamadı.")
        api_key = st.text_input("Google API Key Giriniz", type="password")

if not api_key:
    st.error("Lütfen API Anahtarını sisteme tanıtın.")
    st.stop()

# --- MODEL BULMA (OTOMATİK) ---
def get_best_model(api_key):
    genai.configure(api_key=api_key)
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in models:
            if "gemini-1.5-flash" in m and "latest" in m: return m
        for m in models:
            if "gemini-1.5-flash" in m: return m
        return models[0] if models else None
    except:
        return None

active_model = get_best_model(api_key)
if not active_model:
    st.error("Model bağlanamadı. API Key hatalı olabilir.")
    st.stop()

# --- YÜKLEME ALANLARI ---
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 1. Derinlik / Kademe")
    img_derinlik = st.file_uploader("Derinlik veya Kademe Ekranı", type=["jpg", "png", "jpeg"], key="d")
    
    st.markdown("### 3. Ekstra Veri / Grafik")
    img_ekstra = st.file_uploader("Varsa Grafik/Mum Çubuğu", type=["jpg", "png", "jpeg"], key="e")

with col2:
    st.markdown("### 2. AKD (Aracı Kurum)")
    img_akd = st.file_uploader("AKD Ekranı", type=["jpg", "png", "jpeg"], key="a")

    st.markdown("### 4. Takas Analizi")
    img_takas = st.file_uploader("Takas Ekranı", type=["jpg", "png", "jpeg"], key="t")

# --- ANALİZ MOTORU ---
st.markdown("---")
if st.button("🚀 DETAYLI ANALİZİ BAŞLAT (50 Madde + Trendmetre)", type="primary", use_container_width=True):
    
    input_content = []
    
    system_prompt = """
    Sen dünyanın en iyi Borsa İstanbul 'Quantitative Analyst' ve 'Price Action' uzmanısın.
    GÖREV: Yüklenen borsa ekran görüntülerini analiz et.
    
    KURALLAR:
    1. ASLA "50 Ateş" deme. "POC (Point of Control)", "Hacim Profili" gibi terimler kullan.
    2. Çıktı formatın Streamlit Markdown uyumlu ve RENKLİ olsun (:green[], :red[], :orange[], :blue[]).
    
    RAPOR YAPISI:
    BÖLÜM 1: 💯 HİSSE SKOR KARTI (100 üzerinden puanla)
    BÖLÜM 2: ⏱️ TRENDMETRE (5dk - 1 Haftalık tahmin tablosu)
    BÖLÜM 3: 🔍 50 MADDELİK DEV ANALİZ (Sayısal veri odaklı, en az 50 madde)
    BÖLÜM 4: 🎯 NİHAİ STRATEJİ (Al/Sat/Tut, Stop-Loss, Kar Al bölgeleri)
    """
    
    input_content.append(system_prompt)
    
    loaded_count = 0
    if img_derinlik:
        input_content.append("\n--- GÖRSEL: DERİNLİK/KADEME ---\n")
        input_content.append(Image.open(img_derinlik))
        loaded_count += 1
    if img_akd:
        input_content.append("\n--- GÖRSEL: AKD ANALİZİ ---\n")
        input_content.append(Image.open(img_akd))
        loaded_count += 1
    if img_ekstra:
        input_content.append("\n--- GÖRSEL: EKSTRA GRAFİK/VERİ ---\n")
        input_content.append(Image.open(img_ekstra))
        loaded_count += 1
    if img_takas:
        input_content.append("\n--- GÖRSEL: TAKAS ANALİZİ ---\n")
        input_content.append(Image.open(img_takas))
        loaded_count += 1
        
    if loaded_count == 0:
        st.warning("⚠️ Lütfen analiz için en az 1 adet görsel yükleyiniz.")
    else:
        try:
            model = genai.GenerativeModel(active_model)
            with st.spinner(f"Bulut sunucu verileri işliyor..."):
                response = model.generate_content(input_content)
                st.markdown("## 🧠 Yapay Zeka Raporu")
                st.write(response.text)
        except Exception as e:
            st.error(f"Hata oluştu: {e}")