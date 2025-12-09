import streamlit as st
from PIL import Image
import google.generativeai as genai
import datetime
import time
from urllib.parse import quote

# ==========================================
# 🔐 GÜVENLİK VE AYARLAR
# ==========================================

st.set_page_config(page_title="BIST Yapay Zeka Analiz PRO", layout="wide", page_icon="🐋")

# Görsel stil ayarları
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    h1 { color: #00d4ff !important; }
    h2 { color: #ffbd45 !important; border-bottom: 2px solid #ffbd45; padding-bottom: 10px;}
    h3 { color: #00d4ff !important; }
    div[data-testid="stFileUploader"] { margin-bottom: 20px; }
    .stAlert { border-left: 5px solid #ffbd45; }
    
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
    
    /* Key Status */
    .key-status-pass { color: #00ff00; font-weight: bold; }
    .key-status-fail { color: #ff4444; font-weight: bold; }
    .key-status-limit { color: #ffbd45; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🐋 BIST Yapay Zeka Analiz PRO")
st.info("Küçük Yatırımcının Büyüdüğü Bir Evren..")

# --- 1. API KEY HAVUZU YÖNETİMİ (SADECE SECRETS) ---
api_keys = []

if "GOOGLE_API_KEY" in st.secrets:
    raw_secret = st.secrets["GOOGLE_API_KEY"]
    if "," in raw_secret:
        api_keys = [k.strip() for k in raw_secret.split(",") if k.strip()]
    else:
        api_keys = [raw_secret]
else:
    st.error("🚨 HATA: Secrets dosyasında 'GOOGLE_API_KEY' bulunamadı.")
    st.stop()

api_keys = list(set(api_keys))

if not api_keys:
    st.error("Secrets dosyasındaki anahtar listesi boş.")
    st.stop()

# --- YAN MENÜ ---
with st.sidebar:
    st.header("🔑 Anahtar Yönetimi")
    st.success(f"✅ Sistemde **{len(api_keys)}** adet anahtar yüklü.")
    st.caption("Anahtarlar güvenli alandan (Secrets) çekiliyor.")
    
    st.markdown("---")
    
    if st.button("🔍 Anahtarları Test Et"):
        st.info("Bağlantı kontrol ediliyor...")
        progress_bar = st.progress(0)
        
        for i, key in enumerate(api_keys):
            try:
                genai.configure(api_key=key)
                models = list(genai.list_models())
                if not models: raise Exception("Liste boş")
                masked_key = f"{key[:4]}...{key[-4:]}"
                st.markdown(f"🔑 `{masked_key}` : <span class='key-status-pass'>✅ AKTİF</span>", unsafe_allow_html=True)
            except Exception as e:
                masked_key = f"{key[:4]}...{key[-4:]}"
                err_msg = str(e)
                if "429" in err_msg or "quota" in err_msg.lower():
                    st.markdown(f"🔑 `{masked_key}` : <span class='key-status-limit'>🛑 KOTA DOLU</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"🔑 `{masked_key}` : <span class='key-status-fail'>❌ HATALI</span>", unsafe_allow_html=True)
            progress_bar.progress((i + 1) / len(api_keys))
        st.success("Kontrol Tamamlandı.")

# --- 2. MODEL SEÇİMİ ---
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
    else: raise Exception("Tüm anahtarların kotası dolu!")

# --- SESSION STATE ---
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "loaded_count" not in st.session_state:
    st.session_state.loaded_count = 0
if "active_working_key" not in st.session_state:
    st.session_state.active_working_key = working_key

# ==========================================
# 🐦 YAN MENÜ: X (TWITTER) TARAYICI
# ==========================================
with st.sidebar:
    st.markdown("---")
    st.header("𝕏 (#Hashtag) Tarayıcı")
    st.caption("💬 Gündemi Takip Et 💬")
    
    raw_ticker = st.text_input("Hisse Kodu (Örn: THYAO)", "THYAO").upper()
    clean_ticker = raw_ticker.replace("#", "").replace("$", "").strip()
    
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
# 📤 YÜKLEME ALANLARI (MULTI-UPLOAD GÜNCELLEMESİ)
# ==========================================
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 1. Derinlik Ekranı 💹")
    # accept_multiple_files=True EKLENDİ
    img_derinlik_list = st.file_uploader("Derinlik Görüntüsü (Birden fazla seçilebilir)", type=["jpg", "png", "jpeg"], key="d", accept_multiple_files=True)
    
    st.markdown("### 3. Kademe Analizi 📊")
    img_kademe_list = st.file_uploader("Kademe Analiz Ekranı (Birden fazla seçilebilir)", type=["jpg", "png", "jpeg"], key="e", accept_multiple_files=True)

with col2:
    st.markdown("### 2. AKD (Aracı Kurum) 🤵")
    img_akd_list = st.file_uploader("AKD Ekranı (Birden fazla seçilebilir)", type=["jpg", "png", "jpeg"], key="a", accept_multiple_files=True)
    
    st.markdown("### 4. Takas Analizi 🌍")
    img_takas_list = st.file_uploader("Takas Ekranı (Birden fazla seçilebilir)", type=["jpg", "png", "jpeg"], key="t", accept_multiple_files=True)

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
    
    # --- DİNAMİK BAŞLIK OLUŞTURUCU (LİSTE KONTROLÜ) ---
    dynamic_sections_prompt = ""
    
    # Listeler boş değilse başlık ekle
    if is_summary_mode:
        if img_derinlik_list: dynamic_sections_prompt += "## 💹 DERİNLİK ÖZETİ (En Kritik 3-5 Nokta)\n"
        if img_akd_list: dynamic_sections_prompt += "## 🤵 AKD ÖZETİ (Para Giriş/Çıkış)\n"
        if img_kademe_list: dynamic_sections_prompt += "## 📊 KADEME ÖZETİ (Güçlü Alıcı/Satıcı)\n"
        if img_takas_list: dynamic_sections_prompt += "## 🌍 TAKAS ÖZETİ (Yabancı Durumu)\n"
    else:
        if img_derinlik_list: 
            dynamic_sections_prompt += f"""
            ## 📸 DERİNLİK ANALİZİ (Maks {max_items} Madde)
            (Pozitif > Nötr > Negatif Şeklinde GRUPLA ve RENKLENDİR)
            """
        if img_akd_list:
            dynamic_sections_prompt += f"""
            ## 🏦 AKD (ARACI KURUM) ANALİZİ (Maks {max_items} Madde)
            (Pozitif > Nötr > Negatif Şeklinde GRUPLA ve RENKLENDİR)
            """
        if img_kademe_list:
            dynamic_sections_prompt += f"""
            ## 📊 KADEME & HACİM ANALİZİ (Maks {max_items} Madde)
            (Alt Başlıklar: Kurumsal Alış, Kurumsal Satış, Bireysel Davranış, POC)
            """
        if img_takas_list:
            dynamic_sections_prompt += f"""
            ## 🌍 TAKAS ANALİZİ (Maks {max_items} Madde)
            (Pozitif > Nötr > Negatif Şeklinde GRUPLA ve RENKLENDİR)
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
    
    **GENEL SKOR:** [0-100 Puan]
    
    **ZAMAN BAZLI TREND TABLOSU (Listeleme):**
    AŞAĞIDAKİLERİ TEK TEK RENKLİ MADDE OLARAK YAZ (TABLO YAPMA):
    * **5 Dakika:** [Yön] - [Yorum] (Renkli: :green[] veya :red[])
    * **15 Dakika:** [Yön] - [Yorum]
    * **30 Dakika:** [Yön] - [Yorum]
    * **60 Dakika:** [Yön] - [Yorum]
    * **2 Saat:** [Yön] - [Yorum]
    * **4 Saat:** [Yön] - [Yorum]
    * **Günlük:** [Yön] - [Yorum]
    * **Haftalık:** [Yön] - [Yorum]

    ## 🚀 İŞLEM PLANI (Giriş, Stop, Kar Al)
    """
    
    if not is_summary_mode:
        base_prompt = f"""
        Sen dünyanın en iyi Borsa Fon Yöneticisi ve SMC uzmanısın.
        
        ÖNEMLİ KURALLAR:
        1. **ANALİZ BÖLÜMLERİ:** Her başlık için EN FAZLA {max_items} madde. Pozitif/Nötr/Negatif olarak grupla. Önce :green[YEŞİL], sonra :blue[MAVİ], en son :red[KIRMIZI] sırala. Bölüm sonuna `📊 ÖZET: ✅ X | 🔸 Y | 🔻 Z` ekle.
        2. **GENEL SENTEZ:** Paragraf şeklinde yaz. Akıcı olsun.
        3. **TRENDMETRE:** Kesinlikle MARKDOWN TABLOSU olarak yap. (| Periyot | Yön | Yorum |)
        
        {base_prompt}
        """
    
    input_content.append(base_prompt)
    
    # --- GÖRSELLERİ EKLEME DÖNGÜSÜ (MULTI-UPLOAD DESTEĞİ) ---
    local_loaded_count = 0
    
    # Derinlik Listesi
    if img_derinlik_list:
        input_content.append("\n--- DERİNLİK GÖRSELLERİ ---\n")
        for img_file in img_derinlik_list:
            input_content.append(Image.open(img_file))
        local_loaded_count += 1

    # AKD Listesi
    if img_akd_list:
        input_content.append("\n--- AKD GÖRSELLERİ ---\n")
        for img_file in img_akd_list:
            input_content.append(Image.open(img_file))
        local_loaded_count += 1

    # Kademe Listesi
    if img_kademe_list:
        input_content.append("\n--- KADEME GÖRSELLERİ ---\n")
        for img_file in img_kademe_list:
            input_content.append(Image.open(img_file))
        local_loaded_count += 1

    # Takas Listesi
    if img_takas_list:
        input_content.append("\n--- TAKAS GÖRSELLERİ ---\n")
        for img_file in img_takas_list:
            input_content.append(Image.open(img_file))
        local_loaded_count += 1
        
    if local_loaded_count == 0:
        st.warning("⚠️ Lütfen analiz için en az 1 adet görsel yükleyiniz.")
    else:
        with st.spinner(f"Analiz Süresi, Seçilen İşlem Sayısına Göre Değişkenlik Gösterir..."):
            try:
                final_text = make_resilient_request(input_content, api_keys)
                st.session_state.analysis_result = final_text
                st.session_state.loaded_count = local_loaded_count
                st.rerun()
            except Exception as e:
                st.error(f"HATA: {e}")

# ==========================================
# 📝 SONUÇ GÖSTERİMİ VE SOHBET
# ==========================================

if st.session_state.analysis_result:
    st.markdown("## 🐋 Kurumsal Yapay Zeka Raporu")
    
    if is_summary_mode:
        st.caption("⚡ HIZLI ÖZET MODU Aktif.")
    else:
        st.caption(f"🧠 GELİŞMİŞ MOD Aktif (Sadece Yüklenen {st.session_state.loaded_count} Veri Kategorisi Analiz Edildi).")
    
    st.markdown(st.session_state.analysis_result)
    
    st.markdown("---")
    
    col_header, col_btn = st.columns([8, 2])
    with col_header:
        st.header("💬 Raporla Sohbet Et")
    with col_btn:
        if st.button("🗑️ Sohbeti Temizle"):
            st.session_state.messages = []
            st.rerun()

    st.info("Rapor Hakkındaki Sorularını Sor.")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Sorunuzu yazın..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            genai.configure(api_key=st.session_state.active_working_key)
            model = genai.GenerativeModel(valid_model_name)
            
            chat_context = f"""
            Sen bu analizi yapan Borsa uzmanısın.
            ANALİZ RAPORU (BAĞLAM):
            {st.session_state.analysis_result}
            
            KULLANICI SORUSU:
            {prompt}
            
            Görevin: Sadece rapora ve borsa bilgine dayanarak cevap ver. Kısa, net ve samimi ol.
            Teknik kod blokları gösterme, temiz metin yaz.
            """
            
            try:
                stream = model.generate_content(chat_context, stream=True)
                def stream_parser():
                    for chunk in stream:
                        if chunk.text: yield chunk.text     
                response_text = st.write_stream(stream_parser)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            except Exception as e:
                st.error("Sohbet sırasında hata oluştu.")

