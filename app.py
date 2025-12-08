import streamlit as st
from PIL import Image
import google.generativeai as genai
import datetime
from urllib.parse import quote

# ==========================================
# 🔐 GÜVENLİK VE AYARLAR (BULUT VERSİYONU)
# ==========================================

st.set_page_config(page_title="BIST Analiz Pro V11", layout="wide", page_icon="🐋")

# Görsel stil ayarları
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    h1 { color: #00d4ff !important; }
    h2 { color: #ffbd45 !important; border-bottom: 2px solid #ffbd45; padding-bottom: 10px;}
    h3 { color: #00d4ff !important; }
    div[data-testid="stFileUploader"] { margin-bottom: 20px; }
    .stAlert { border-left: 5px solid #ffbd45; }
    
    /* İstatistik Kutusu Stili */
    .stat-box {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #444;
        margin-top: 10px;
        margin-bottom: 20px;
        font-weight: bold;
        color: #fff;
    }
    
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

st.title("🐋 BIST Pro V11: Sohbet & Derin Analiz")
st.info("20+ Madde Detaylı Yorum, İstatistik Özetleri ve 'Raporla Sohbet' Özelliği.")

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

# --- SESSION STATE (SOHBET HAFIZASI) ---
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# ==========================================
# 🐦 YAN MENÜ: X (TWITTER) TARAYICI
# ==========================================
with st.sidebar:
    st.markdown("---")
    st.header("🐦 X (#Hashtag) Tarayıcı")
    
    raw_ticker = st.text_input("Hisse Kodu (Örn: THYAO)", "THYAO").upper()
    clean_ticker = raw_ticker.replace("#", "").replace("$", "").strip()
    
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
        search_query = f"#{clean_ticker} lang:tr until:{next_day} since:{selected_date} min_faves:5"
        encoded_query = quote(search_query)
        x_url = f"https://x.com/search?q={encoded_query}&src=typed_query&f=top"
        btn_text = f"🔥 <b>{selected_date}</b> Tarihli<br>Popüler <b>#{clean_ticker}</b> Tweetleri"
        
    else: 
        st.caption("Tarih farketmeksizin, şu an atılan en son tweetleri listeler.")
        search_query = f"#{clean_ticker} lang:tr"
        encoded_query = quote(search_query)
        x_url = f"https://x.com/search?q={encoded_query}&src=typed_query&f=live"
        btn_text = f"⏱️ <b>#{clean_ticker}</b> Hakkında<br>Son Dakika Akışını Gör"

    st.markdown(f"""<a href="{x_url}" target="_blank" class="x-btn">{btn_text}</a>""", unsafe_allow_html=True)

# ==========================================
# 📤 YÜKLEME ALANLARI
# ==========================================
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 1. Derinlik Ekranı")
    img_derinlik = st.file_uploader("Derinlik Görüntüsü", type=["jpg", "png", "jpeg"], key="d")
    st.markdown("### 3. Kademe Analizi")
    st.caption("Fiyat seviyelerine göre hacim dağılımı")
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
if st.button("🐋 DETAYLI ANALİZİ BAŞLAT", type="primary", use_container_width=True):
    
    # Yeni analiz başladığında hafızayı temizle
    st.session_state.messages = [] 
    input_content = []
    
    # --- GÜÇLENDİRİLMİŞ PROMPT (20 MADDE + SAYAÇ) ---
    system_prompt = f"""
    Sen dünyanın en iyi Borsa Fon Yöneticisi ve SMC (Smart Money Concepts) uzmanısın.
    HEDEF HİSSE: #{clean_ticker}
    
    GÖREV: Yüklenen her görseli mikroskop altında incele.
    
    ÖNEMLİ KURALLAR:
    1. **SAYI ZORUNLULUĞU:** Her ana başlık altında (Derinlik, AKD, Kademe, Takas) madde madde analiz yaparken, **EN AZ 20 FARKLI GÖZLEM** yazacaksın. Kısa kesmek yasak. Gerekirse en küçük lot farkını bile yaz.
    2. **İSTATİSTİK KUTUSU:** Her bölümün en altına, o bölümdeki verilerin duygu durumunu sayıp şu formatta bir kutu ekle:
       `📊 VERİ ÖZETİ: ✅ Olumlu: [Sayı] | 🔻 Olumsuz: [Sayı] | 🔸 Nötr: [Sayı]`
    3. **RENKLER:** :green[Pozitif], :red[Negatif], :orange[Nötr], :blue[Bilgi].
    
    --- RAPOR FORMATI ---
    
    ## BÖLÜM 1: 📸 DERİNLİK ANALİZİ (En az 20 Madde)
    - (Alıcı/Satıcı lot farkları, kademe boşlukları, pasif emirler, spread, tahta hızı vb. hakkında 20 detaylı madde...)
    - [Bölüm sonuna İstatistik Kutusu Ekle]
    
    ## BÖLÜM 2: 🏦 AKD (ARACI KURUM) ANALİZİ (En az 20 Madde)
    - (Para girişi, İlk 5 kurum, Diğer kalemi, BofA/YF robot hareketleri hakkında 20 detaylı madde...)
    - [Bölüm sonuna İstatistik Kutusu Ekle]
    
    ## BÖLÜM 3: 📊 KADEME & HACİM ANALİZİ (En az 20 Madde)
    - (Bu bölüm çok kritik. Alt Başlıkları Kullan:)
      * **En Güçlü Kurumsal Alışlar:** (Fiyat ve Lot belirt)
      * **En Güçlü Kurumsal Satışlar:** (Direnç duvarları)
      * **Bireysel (Küçük Yatırımcı) Davranışı:**
      * **Akümülasyon mu Dağıtım mı?:**
      * **POC (En yoğun hacim) Bölgesi:**
    - [Bölüm sonuna İstatistik Kutusu Ekle]
    
    ## BÖLÜM 4: 🌍 TAKAS ANALİZİ (En az 20 Madde)
    - (Citi/Doçe yabancı payı, haftalık değişim, malın toplu/dağınık olması hakkında 20 detaylı madde...)
    - [Bölüm sonuna İstatistik Kutusu Ekle]
    
    ## BÖLÜM 5: 🐋 GENEL SENTEZ (BALİNA İZİ)
    - Kurumsal oyun planı nedir? Tuzak var mı?
    
    ## BÖLÜM 6: 💯 SKOR KARTI & TRENDMETRE (TABLO)
    - 5dk, 15dk, 30dk, 60dk, 2s, 4s, Günlük, Haftalık için Tablo.
    
    ## BÖLÜM 7: 🚀 İŞLEM PLANI
    - ✅ Giriş, 🛑 Stop, 💰 Kar Al.
    """
    
    input_content.append(system_prompt)
    
    loaded_count = 0
    if img_derinlik:
        input_content.append("\n--- DERİNLİK ---\n"); input_content.append(Image.open(img_derinlik)); loaded_count += 1
    if img_akd:
        input_content.append("\n--- AKD ---\n"); input_content.append(Image.open(img_akd)); loaded_count += 1
    if img_kademe:
        input_content.append("\n--- KADEME ---\n"); input_content.append(Image.open(img_kademe)); loaded_count += 1
    if img_takas:
        input_content.append("\n--- TAKAS ---\n"); input_content.append(Image.open(img_takas)); loaded_count += 1
        
    if loaded_count == 0:
        st.warning("⚠️ Lütfen analiz için en az 1 adet görsel yükleyiniz.")
    else:
        try:
            model = genai.GenerativeModel(active_model)
            with st.spinner(f"Kurumsal analiz yapılıyor... 20+ Madde çıkarılıyor..."):
                response = model.generate_content(input_content)
                # SONUCU HAFIZAYA KAYDET
                st.session_state.analysis_result = response.text
                st.rerun() # Sayfayı yenile ki sonuç ekrana gelsin
        except Exception as e:
            st.error(f"Hata oluştu: {e}")

# ==========================================
# 📝 SONUÇ GÖSTERİMİ VE SOHBET
# ==========================================

if st.session_state.analysis_result:
    st.markdown("## 🐋 Kurumsal Yapay Zeka Raporu")
    st.markdown(st.session_state.analysis_result)
    
    st.markdown("---")
    st.header("💬 Raporla Sohbet Et")
    st.info("Yukarıdaki rapora dair sorularını sor (Örn: 'Stop-loss sence neden bu kadar yakın?', 'BofA toplamda ne kadar almış?')")

    # Sohbet Geçmişini Göster
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

   # Kullanıcıdan Girdi Al
    if prompt := st.chat_input("Sorunuzu yazın..."):
        # Kullanıcı mesajını ekle
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Yapay Zeka Cevabı
        with st.chat_message("assistant"):
            model = genai.GenerativeModel(active_model)
            
            # Bağlam (Context) Oluşturma
            chat_context = f"""
            Sen bu analizi yapan Borsa uzmanısın.
            
            ANALİZ RAPORU (BAĞLAM):
            {st.session_state.analysis_result}
            
            KULLANICI SORUSU:
            {prompt}
            
            Görevin: Sadece rapora ve borsa bilgine dayanarak cevap ver. Kısa, net ve samimi ol.
            Teknik kod blokları gösterme, sadece metin olarak cevapla.
            """
            
            # --- DÜZELTME BURADA YAPILDI ---
            try:
                # Stream (Akış) başlatılıyor
                stream = model.generate_content(chat_context, stream=True)
                
                # Gelen karmaşık veriyi (Chunk) sadece METNE (.text) çeviren fonksiyon
                def stream_parser():
                    for chunk in stream:
                        if chunk.text:
                            yield chunk.text
                
                # Ekrana temiz metni yazdır
                response_text = st.write_stream(stream_parser)
                
                # Cevabı hafızaya ekle
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
            except Exception as e:
                st.error("Bir hata oluştu, lütfen tekrar deneyin.")
