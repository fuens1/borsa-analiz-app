import streamlit as st
from PIL import Image
import google.generativeai as genai
import datetime

# ==========================================
# 🔐 GÜVENLİK VE AYARLAR (BULUT VERSİYONU)
# ==========================================

st.set_page_config(page_title="BIST Analiz Pro V6", layout="wide", page_icon="🐋")

# Görsel stil ayarları
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    h1 { color: #00d4ff !important; }
    h3 { color: #ffbd45 !important; }
    div[data-testid="stFileUploader"] { margin-bottom: 20px; }
    .stAlert { border-left: 5px solid #ffbd45; }
    
    /* X Butonu Stili */
    .x-btn {
        display: inline-block;
        background-color: #000000;
        color: white !important;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none;
        font-size: 16px;
        border-radius: 8px;
        border: 1px solid #333;
        width: 100%;
        margin-top: 10px;
    }
    .x-btn:hover {
        background-color: #333;
        border-color: #fff;
    }
</style>
""", unsafe_allow_html=True)

st.title("🐋 BIST Pro V6: Balina Takibi & X Zaman Makinesi")
st.info("Yapay Zeka ile Teknik Analiz + X (Twitter) Geçmiş Sentiment Taraması")

# --- API KEY KONTROLÜ (SECRETS) ---
api_key = None
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    with st.sidebar:
        st.header("🔑 Ayarlar")
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

# ==========================================
# 🐦 YAN MENÜ: X (TWITTER) ZAMAN MAKİNESİ
# ==========================================
with st.sidebar:
    st.markdown("---")
    st.header("🐦 X (Twitter) Zaman Makinesi")
    st.info("Geçmiş tarihte o hisse hakkında en çok konuşulanları bulur.")
    
    ticker = st.text_input("Hisse Kodu (Örn: THYAO)", "THYAO").upper()
    selected_date = st.date_input("Hangi Tarihe Gidilsin?", datetime.date.today())
    
    # Tarih formatlama ve Link Üretme
    # X Arama Formatı: $THYAO until:2023-12-02 since:2023-12-01 min_faves:10
    next_day = selected_date + datetime.timedelta(days=1)
    
    search_query = f"${ticker} lang:tr until:{next_day} since:{selected_date}"
    x_url = f"https://x.com/search?q={search_query}&src=typed_query&f=top"
    
    st.markdown(f"""
    <a href="{x_url}" target="_blank" class="x-btn">
       🔍 <b>{selected_date}</b> Tarihli<br>En Popüler <b>#{ticker}</b> Gönderilerini Gör
    </a>
    """, unsafe_allow_html=True)
    st.caption("*Bu özellik X API kısıtlamalarına takılmadan, doğrudan geçmişteki en popüler tweetlere ulaşmanızı sağlar.*")

# ==========================================
# 📤 YÜKLEME ALANLARI
# ==========================================
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 1. Derinlik Ekranı")
    img_derinlik = st.file_uploader("Derinlik Görüntüsü", type=["jpg", "png", "jpeg"], key="d")
    
    st.markdown("### 3. Kademe Analizi")
    img_kademe = st.file_uploader("Kademe Analiz Ekranı", type=["jpg", "png", "jpeg"], key="e")

with col2:
    st.markdown("### 2. AKD (Aracı Kurum)")
    img_akd = st.file_uploader("AKD Ekranı", type=["jpg", "png", "jpeg"], key="a")

    st.markdown("### 4. Takas Analizi")
    img_takas = st.file_uploader("Takas Ekranı", type=["jpg", "png", "jpeg"], key="t")

# ==========================================
# 🚀 ANALİZ MOTORU
# ==========================================
st.markdown("---")
if st.button("🐋 DEV ANALİZİ BAŞLAT (Balina + Giriş Seviyesi)", type="primary", use_container_width=True):
    
    input_content = []
    
    system_prompt = f"""
    Sen dünyanın en iyi Borsa İstanbul 'Quantitative Analyst' ve 'Smart Money' (Akıllı Para) uzmanısın.
    GÖREV: Yüklenen borsa ekran görüntülerini analiz et.
    
    BAĞLAM:
    Kullanıcı şu hisse ile ilgileniyor: {ticker} (Eğer görseller başka hisseye aitse görseldekini baz al).
    
    TERMİNOLOJİ KURALLARI:
    1. "POC (Point of Control)", "Hacim Profili", "VWAP", "Smart Money Concepts (SMC)" terimlerini kullan.
    2. Çıktı formatın RENKLİ olsun (:green[], :red[], :orange[], :blue[]).
    
    RAPOR YAPISI (SIRAYLA VE EKSİKSİZ UYGULA):
    
    BÖLÜM 1: 💯 HİSSE SKOR KARTI & TRENDMETRE
    - 100 üzerinden puanla.
    - 5dk ile 1 Haftalık periyotlar için bir tahmin tablosu oluştur.
    
    BÖLÜM 2: 🐋 BALİNA VE KURUMSAL İZ SÜRME (SMC)
    - Hangi kurumlar (BofA, YF, Citi, Global vb.) tahtada oyun kuruyor?
    - Balinalar malı topluyor mu (Accumulation), dağıtıyor mu (Distribution)?
    - **Kurumsal ALIŞ Seviyeleri:** Kurumsalların en güçlü alım yaptığı, duvar ördüğü fiyatları tespit et.
    - **Kurumsal SATIŞ Seviyeleri:** Kurumsalların satış yığdığı dirençleri yaz.
    
    BÖLÜM 3: 🔍 50 MADDELİK MİKRO ANALİZ
    - Sayısal veriler, lot farkları, kademe boşlukları üzerine en az 50 madde.
    
    BÖLÜM 4: 🚀 İŞLEM PLANI VE GİRİŞ SEVİYELERİ (EN ALTA EKLE)
    - Burası hayati önem taşıyor. Yatırımcıya net rakamlar ver.
    - ✅ **En Uygun GİRİŞ Seviyesi (Entry Point):** Fiyat hacimli bölgeye veya kurumsal maliyete nerede temas ediyor?
    - 🛑 **Zarar Kes (Stop-Loss):** Hangi seviye kırılırsa formasyon bozulur?
    - 💰 **Kar Al (Take Profit):** İlk direnç ve ana hedef neresi?
    - **Nihai Karar:** (MALA GİR / DESTEĞE GELMESİNİ BEKLE / SAT KAÇ)
    """
    
    input_content.append(system_prompt)
    
    loaded_count = 0
    if img_derinlik:
        input_content.append("\n--- GÖRSEL: DERİNLİK EKRANI ---\n")
        input_content.append(Image.open(img_derinlik))
        loaded_count += 1
    if img_akd:
        input_content.append("\n--- GÖRSEL: AKD (ARACI KURUM) ANALİZİ ---\n")
        input_content.append(Image.open(img_akd))
        loaded_count += 1
    if img_kademe:
        input_content.append("\n--- GÖRSEL: KADEME ANALİZİ (HACİM DAĞILIMI) ---\n")
        input_content.append(Image.open(img_kademe))
        loaded_count += 1
    if img_takas:
        input_content.append("\n--- GÖRSEL: TAKAS ANALİZİ ---\n")
        input_content.append(Image.open(img_takas))
        loaded_count += 1
        
    if loaded_count == 0:
        st.warning("⚠️ Lütfen Analiz İçin En Az 1 Adet Görsel Yükleyiniz.")
    else:
        try:
            model = genai.GenerativeModel(active_model)
            with st.spinner(f"Balinalar taranıyor... {ticker} verileri işleniyor..."):
                response = model.generate_content(input_content)
                st.markdown("## 🐋 Yapay Zeka Raporu")
                st.write(response.text)
        except Exception as e:
            st.error(f"Hata oluştu: {e}")
