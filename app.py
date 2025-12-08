import streamlit as st
from PIL import Image
import google.generativeai as genai
import datetime
from urllib.parse import quote

# ==========================================
# 🔐 GÜVENLİK VE AYARLAR (BULUT VERSİYONU)
# ==========================================

st.set_page_config(page_title="BIST Analiz Pro V10", layout="wide", page_icon="🐋")

# Görsel stil ayarları
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    h1 { color: #00d4ff !important; }
    h2 { color: #ffbd45 !important; border-bottom: 2px solid #ffbd45; padding-bottom: 10px;}
    h3 { color: #00d4ff !important; }
    div[data-testid="stFileUploader"] { margin-bottom: 20px; }
    .stAlert { border-left: 5px solid #ffbd45; }
    
    /* X Butonu Stili */
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
        border-color: #1d9bf0; /* X Mavisi */
        color: #1d9bf0 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🐋 BIST Pro V10: Kurumsal Düzey Derin Analiz")
st.info("Her veri seti ayrı ayrı yorumlanır, ardından Balina (SMC) sentezi ve detaylı Trendmetre oluşturulur.")

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
# 🐦 YAN MENÜ: X (TWITTER) TARAYICI
# ==========================================
with st.sidebar:
    st.markdown("---")
    st.header("🐦 X (#Hashtag) Tarayıcı")
    
    # Hisse Kodu Girişi
    raw_ticker = st.text_input("Hisse Kodu (Örn: THYAO)", "THYAO").upper()
    clean_ticker = raw_ticker.replace("#", "").replace("$", "").strip()
    
    # MOD SEÇİMİ
    search_mode = st.radio(
        "Arama Tipi:",
        ("🔥 En Popüler (Geçmiş)", "⏱️ Son Dakika (Canlı)")
    )
    
    x_url = ""
    btn_text = ""
    
    if search_mode == "🔥 En Popüler (Geçmiş)":
        st.caption("Belirli bir tarihteki en etkileşimli tweetleri getirir.")
        selected_date = st.date_input("Hangi Tarih?", datetime.date.today())
        next_day = selected_date + datetime.timedelta(days=1)
        
        # Filtre: Tarih aralığı + En az 5 Fav
        search_query = f"#{clean_ticker} lang:tr until:{next_day} since:{selected_date} min_faves:5"
        encoded_query = quote(search_query)
        x_url = f"https://x.com/search?q={encoded_query}&src=typed_query&f=top"
        btn_text = f"🔥 <b>{selected_date}</b> Tarihli<br>Popüler <b>#{clean_ticker}</b> Tweetleri"
        
    else: # SON DAKİKA MODU
        st.caption("Tarih farketmeksizin, şu an atılan en son tweetleri listeler.")
        
        search_query = f"#{clean_ticker} lang:tr"
        encoded_query = quote(search_query)
        x_url = f"https://x.com/search?q={encoded_query}&src=typed_query&f=live"
        btn_text = f"⏱️ <b>#{clean_ticker}</b> Hakkında<br>Son Dakika Akışını Gör"

    # Butonu Oluştur
    st.markdown(f"""
    <a href="{x_url}" target="_blank" class="x-btn">
       {btn_text}
    </a>
    """, unsafe_allow_html=True)


# ==========================================
# 📤 YÜKLEME ALANLARI
# ==========================================
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 1. Derinlik Ekranı")
    img_derinlik = st.file_uploader("Derinlik Görüntüsü", type=["jpg", "png", "jpeg"], key="d")
    
    st.markdown("### 3. Kademe Analizi")
    st.caption("Fiyat seviyelerine göre hacim dağılımı (Price Ladder)")
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
if st.button("🐋 KURUMSAL ANALİZİ BAŞLAT", type="primary", use_container_width=True):
    
    input_content = []
    
    # --- PROMPT MİMARİSİ (BEYİN) ---
    system_prompt = f"""
    Sen dünyanın en iyi 'Hedge Fund' Yöneticisi ve 'Smart Money' (SMC) uzmanısın.
    GÖREV: Yüklenen borsa verilerini (Derinlik, AKD, Kademe, Takas) profesyonelce analiz et.
    
    HEDEF HİSSE: #{clean_ticker}
    
    KURALLAR:
    1. Her görseli önce KENDİ BAŞLIĞI altında detaylıca incele.
    2. Sonra bu parçaları birleştirip BÜYÜK RESMİ (Balina Hareketini) çiz.
    3. Renk Kodları: :green[Pozitif], :red[Negatif], :orange[Uyarı/Nötr], :blue[Kurumsal Veri].
    
    --- RAPOR ŞABLONU (BU YAPIYI BOZMA) ---
    
    ## BÖLÜM 1: 📸 GÖRSEL BAZLI TEKNİK ÇÖZÜMLEME
    (Sadece yüklenen görseller için aşağıdaki başlıkları aç ve yorumla)
    
    ### 1.1 DERİNLİK ANALİZİ
    - Alıcı/Satıcı dengesi nasıl? (Lot farkı)
    - Pasif emirlerde (Alt/Üst kademe) yığılma nerede?
    - Spread (Makas) durumu ve tahta hızı.
    
    ### 1.2 AKD (ARACI KURUM) ANALİZİ
    - Net Para Girişi/Çıkışı var mı?
    - İlk 5 Kurum (Takasbank verisi) alıcı mı satıcı mı?
    - "Diğer" kalemi ne yapıyor? (Küçük yatırımcı mal mı alıyor, mal mı satıyor?)
    
    ### 1.3 KADEME ANALİZİ (ÇOK DETAYLI OLACAK)
    - **En Güçlü Kurumsal Alış Seviyeleri:** Hangi fiyatta "Iceberg" veya yüklü blok alım var?
    - **En Güçlü Kurumsal Satış Seviyeleri:** Direnç olarak çalışan kurumsal duvarlar.
    - **Bireysel Davranışlar:** Küçük yatırımcı panik mi yapıyor, FOMO'ya mı kapılmış?
    - **Savaş Alanı (POC):** En çok hacmin döndüğü kritik fiyat seviyesi.
    - **Trend Sinyali:** Bu yapı bir "Akümülasyon" (Toplama) mı yoksa "Dağıtım" (Mal çakma) mı?
    
    ### 1.4 TAKAS ANALİZİ
    - Yabancı (Citi/Doçe) payı değişimi.
    - Haftalık/Aylık değişimde mal toplu mu dağınık mı?
    
    ---
    
    ## BÖLÜM 2: 🐋 BALİNA VE KURUMSAL İZ SÜRME (SMC & SENTEZ)
    (Burada yukarıdaki tüm verileri birleştirerek yorumla)
    - Tahtanın "Market Maker"ı (Oyun Kurucusu) kim? BofA, YF, Yatırım Finansman ne yapıyor?
    - Robotlar hangi algoritmaya göre çalışıyor (Trend follower vs. Mean Reversion)?
    - Balinaların ayak izleri: Gizli toplama veya fake yükseliş (Bull Trap) var mı?
    
    ---
    
    ## BÖLÜM 3: 💯 HİSSE SKOR KARTI & DETAYLI TRENDMETRE
    **GENEL SKOR:** (0-100 Arası Puan ver)
    
    **ZAMAN BAZLI TREND ANALİZİ TABLOSU:**
    Aşağıdaki vadeler için bir tablo oluştur: [Vade | Yön | Güven Oranı | Kısa Yorum]
    - 5 Dakika
    - 15 Dakika
    - 30 Dakika
    - 60 Dakika
    - 2 Saat
    - 4 Saat
    - 1 Gün (Günlük)
    - 1 Hafta (Haftalık)
    *(Not: Derinlik kısa vadeyi, Takas uzun vadeyi etkiler. Buna göre simüle et.)*
    
    ---
    
    ## BÖLÜM 4: 🚀 PROFESYONEL İŞLEM PLANI
    - ✅ **Sniper Giriş Seviyesi (Entry):** Nokta atışı fiyat aralığı.
    - 🛑 **Stop-Loss (Zarar Kes):** İptal seviyesi.
    - 💰 **Take Profit (Kar Al):** Hedef fiyatlar.
    - **NİHAİ KARAR:** (Agresif Al / Kademeli Al / İzle / Sat / Açığa Sat)
    """
    
    input_content.append(system_prompt)
    
    loaded_count = 0
    if img_derinlik:
        input_content.append("\n--- RESİM: DERİNLİK EKRANI ---\n")
        input_content.append(Image.open(img_derinlik))
        loaded_count += 1
    if img_akd:
        input_content.append("\n--- RESİM: AKD (ARACI KURUM) ANALİZİ ---\n")
        input_content.append(Image.open(img_akd))
        loaded_count += 1
    if img_kademe:
        input_content.append("\n--- RESİM: KADEME ANALİZİ (PRICE LADDER) ---\n")
        input_content.append(Image.open(img_kademe))
        loaded_count += 1
    if img_takas:
        input_content.append("\n--- RESİM: TAKAS ANALİZİ ---\n")
        input_content.append(Image.open(img_takas))
        loaded_count += 1
        
    if loaded_count == 0:
        st.warning("⚠️ Lütfen Analiz İçin En Az 1 Adet Görsel Yükleyiniz.")
    else:
        try:
            model = genai.GenerativeModel(active_model)
            with st.spinner(f"Kurumsal veriler işleniyor... #{clean_ticker} için SMC analizi yapılıyor..."):
                response = model.generate_content(input_content)
                st.markdown("## 🐋 Kurumsal Yapay Zeka Raporu")
                st.write(response.text)
        except Exception as e:
            st.error(f"Hata oluştu: {e}")
