import streamlit as st
import yt_dlp
import os
import glob
import math
import re

# --- 1. CONFIGURARE PAGINĂ & DESIGN HIPSTER ---
st.set_page_config(page_title="Transcript Barista", page_icon="☕", layout="centered")

# CSS pentru stilul Pastel / Hipster Coffee
st.markdown("""
    <style>
        /* Fundal general - Crem Latte */
        .stApp {
            background-color: #FDFBF7;
            color: #4A4036;
        }
        
        /* Titluri */
        h1, h2, h3 {
            color: #4A4036 !important;
            font-family: 'Helvetica Neue', sans-serif;
            font-weight: 300;
        }
        
        /* Input text & Slider */
        .stTextInput > div > div > input {
            background-color: #FFFFFF;
            color: #4A4036;
            border: 1px solid #D8C3A5;
            border-radius: 12px;
            padding: 10px;
        }
        
        /* Butonul Principal - Stil Matcha */
        .stButton > button {
            background-color: #A3B18A;
            color: #FFFFFF;
            border: none;
            border-radius: 25px;
            padding: 10px 24px;
            font-weight: bold;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            width: 100%;
        }
        .stButton > button:hover {
            background-color: #588157;
            color: #FFFFFF;
            transform: translateY(-2px);
        }
        
        /* Sidebar styling - Stil Carton Reciclat */
        section[data-testid="stSidebar"] {
            background-color: #EAE0D5;
            border-right: 1px solid #C6AC8F;
        }
        
        /* Expander (Acordeon) styling */
        .streamlit-expanderHeader {
            background-color: #FFFFFF;
            border-radius: 10px;
            border: 1px solid #EAE0D5;
            color: #4A4036;
        }
        
        /* Code blocks styling - Ascuns vizual, curat */
        .stCode {
            background-color: #FFF;
            border: 1px dashed #C6AC8F;
        }
        
        /* Mesaje de status */
        .stAlert {
            border-radius: 10px;
            background-color: #FFF0F5; /* Roz pal */
            color: #4A4036;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. HEADER ---
st.title("☕ YouTube Transcript Barista")
st.markdown("*Prepară transcriptul perfect pentru ChatGPT, fără cofeină.*")

# --- 3. SIDEBAR (SETĂRI) ---
with st.sidebar:
    st.header("⚙️ Setări Măcinare")
    
    # 3.1 Selector Limbă (AICI ESTE BUTONUL DE LIMBĂ CERUT)
    lang_options = {
        "🇷🇴 Română": "ro",
        "🇬🇧 Engleză": "en",
        "🇫🇷 Franceză": "fr",
        "🇪🇸 Spaniolă": "es",
        "🇩🇪 Germană": "de",
        "🇮🇹 Italiană": "it"
    }
    st.write("**1. Alege Limba Video-ului:**")
    selected_lang_label = st.selectbox("Limbă", list(lang_options.keys()), label_visibility="collapsed")
    selected_lang_code = lang_options[selected_lang_label]
    
    st.markdown("---")
    
    # 3.2 Slider Mărime (AICI ESTE SLIDERUL CERUT)
    st.write("**2. Dimensiune Porție (Caractere):**")
    CHUNK_SIZE = st.slider(
        "Mărime Chunk", 
        min_value=2000, 
        max_value=30000, 
        value=15000, 
        step=1000,
        label_visibility="collapsed",
        help="Alege cât text să fie în fiecare 'înghițitură' pentru AI."
    )
    st.caption(f"Setat la: {CHUNK_SIZE} caractere")

# --- 4. PROMPT AI ---
PROMPT_INTRO = """
Rol: Ești un analist de conținut expert.
Context: Aceasta este partea {part} din {total} a transcriptului.

Sarcina:
1. Analizează textul (tradu în Română dacă e cazul).
2. Extrage ideile principale, cifrele și argumentele.
3. Ignoră introducerile și reclamele.
4. Formatează cu Titluri și Bullet Points.

Transcript:
--------------------------------------------------
"""

# --- 5. INTERFAȚA PRINCIPALĂ ---
st.write("Link-ul YouTube:")
url = st.text_input("Link", label_visibility="collapsed", placeholder="https://youtube.com/...")

if st.button("🍵 Prepară Transcriptul"):
    if not url:
        st.warning("⚠️ Te rog pune un link valid (comanda e goală).")
    else:
        status = st.empty()
        status.info("🍂 Culegem boabele (Descarc subtitrarea)...")
        
        # Configurare yt-dlp
        options = {
            'skip_download': True,
            'writeautomaticsub': True,
            'writesubtitles': True,
            'subtitleslangs': [selected_lang_code],
            'outtmpl': 'temp_stream',
            'quiet': True,
            'no_warnings': True
        }

        try:
            # Curățare fișiere vechi
            for f in glob.glob("temp_stream*"): 
                try: os.remove(f)
                except: pass

            # Descărcare
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([url])

            # Găsire fișier
            files = glob.glob("temp_stream*.vtt")
            
            if files:
                filename = files[0]
                
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Procesare text
                full_text_list = []
                seen = set()
                for line in lines:
                    line = line.strip()
                    if "-->" in line or line == "WEBVTT" or not line: continue
                    if line.startswith("<") and line.endswith(">"): continue
                    if "<" in line and ">" in line:
                        line = re.sub(r'<[^>]+>', '', line)
                    if line in seen: continue
                    seen.add(line)
                    full_text_list.append(line)

                whole_text = " ".join(full_text_list)
                
                if len(whole_text) < 50:
                    status.error("❌ Subtitrarea pare goală.")
                else:
                    total_chars = len(whole_text)
                    num_chunks = math.ceil(total_chars / CHUNK_SIZE)
                    
                    status.success(f"✅ Gata! Avem {num_chunks} porții proaspete.")
                    
                    st.markdown("### 📋 Porțiile tale (Click să deschizi & Copy)")
                    
                    # Generare Bucăți
                    for i in range(num_chunks):
                        start = i * CHUNK_SIZE
                        end = start + CHUNK_SIZE
                        chunk_text = whole_text[start:end]
                        
                        header = PROMPT_INTRO.format(part=i+1, total=num_chunks)
                        final_block = header + chunk_text
                        
                        # AICI E SOLUȚIA PENTRU "NU VREAU SA VAD TEXTUL, DOAR COPY"
                        # Folosim st.expander care stă închis implicit.
                        label = f"🍪 Partea {i+1} (din {num_chunks})"
                        with st.expander(label, expanded=False):
                            st.caption("Apasă iconița mică de 'Copy' din dreapta sus a chenarului 👇")
                            st.code(final_block, language="text")

                try: os.remove(filename)
                except: pass

            else:
                status.error(f"❌ Nu am găsit subtitrări pentru limba selectată ({selected_lang_label}).")
                
        except Exception as e:
            status.error(f"Eroare la preparare: {str(e)}")
            
