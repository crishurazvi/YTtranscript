import streamlit as st
import yt_dlp
import os
import glob
import math
import re

# --- 1. CONFIGURARE PAGINĂ & DARK MODE ---
st.set_page_config(page_title="Dark Roast Transcript", page_icon="☕", layout="centered")

# CSS pentru stilul Dark Espresso
st.markdown("""
    <style>
        /* Fundal general - Dark Espresso */
        .stApp {
            background-color: #121212;
            color: #E0E0E0;
        }
        
        /* Titluri */
        h1, h2, h3 {
            color: #D4A373 !important; /* Culoare spumă de cafea */
            font-family: 'Helvetica Neue', sans-serif;
            font-weight: 300;
        }
        
        /* Input text & Selectbox & Slider - Dark Mode */
        .stTextInput > div > div > input, 
        .stSelectbox > div > div > div {
            background-color: #2C2C2C;
            color: #FFFFFF;
            border: 1px solid #4A4A4A;
            border-radius: 8px;
        }
        
        /* Etichete (Labels) */
        .stMarkdown p, label {
            color: #B0B0B0 !important;
        }
        
        /* Butonul Principal - Stil Ristretto (Accent puternic) */
        .stButton > button {
            background-color: #BC6C25; /* Caramel închis */
            color: #FFFFFF;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-weight: bold;
            width: 100%;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            background-color: #D4A373;
            color: #121212;
        }
        
        /* Expander (Acordeon) styling pentru Dark Mode */
        .streamlit-expanderHeader {
            background-color: #1E1E1E;
            border-radius: 5px;
            border: 1px solid #333;
            color: #E0E0E0;
        }
        
        /* Code blocks styling */
        .stCode {
            background-color: #000 !important;
            border: 1px solid #333;
        }
        
        /* Mesaje de status */
        .stAlert {
            background-color: #2C2C2C;
            color: #E0E0E0;
            border: 1px solid #BC6C25;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. HEADER ---
st.title("☕ Dark Roast Transcript")
st.markdown("---")

# --- 3. CONTROALE (Acum în pagina principală) ---
# Folosim coloane pentru a pune setările una lângă alta
col1, col2 = st.columns(2)

with col1:
    # 3.1 Selector Limbă
    lang_options = {
        "🇬🇧 English": "en",
        "🇷🇴 Română": "ro",
        "🇫🇷 Franceză": "fr",
        "🇪🇸 Spaniolă": "es",
        "🇩🇪 Germană": "de",
        "🇮🇹 Italiană": "it"
    }
    # Listăm cheile pentru a seta default pe index 0 (English)
    lang_keys = list(lang_options.keys())
    
    st.write("**Limbă Video:**")
    selected_lang_label = st.selectbox(
        "Limbă", 
        lang_keys, 
        index=0, # Index 0 este English acum
        label_visibility="collapsed"
    )
    selected_lang_code = lang_options[selected_lang_label]

with col2:
    # 3.2 Slider Mărime
    st.write("**Dimensiune (Caractere):**")
    CHUNK_SIZE = st.slider(
        "Mărime Chunk", 
        min_value=2000, 
        max_value=30000, 
        value=15000, 
        step=1000,
        label_visibility="collapsed"
    )

# --- 4. INPUT URL ---
st.write("") # Spațiu
st.write("**Link YouTube:**")
url = st.text_input("Link", label_visibility="collapsed", placeholder="https://youtube.com/...")

# --- 5. PROMPT AI ---
PROMPT_INTRO = """
Rol: Ești un analist de conținut expert.
Context: Aceasta este partea {part} din {total} a transcriptului.

Sarcina:
1. Analizează textul (tradu în {lang} dacă e cazul).
2. Extrage ideile principale, cifrele și argumentele.
3. Ignoră introducerile și reclamele.
4. Formatează cu Titluri și Bullet Points.

Transcript:
--------------------------------------------------
"""

# --- 6. BUTON ACȚIUNE ---
st.write("")
if st.button("🌑 Generează Transcriptul"):
    if not url:
        st.warning("⚠️ Te rog pune un link valid.")
    else:
        status = st.empty()
        status.info("☕ Se prepară (Descarc subtitrarea)...")
        
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
                    
                    status.success(f"✅ Gata! {num_chunks} părți pregătite.")
                    st.markdown("---")
                    
                    # Generare Bucăți - Stil Minimalist
                    for i in range(num_chunks):
                        start = i * CHUNK_SIZE
                        end = start + CHUNK_SIZE
                        chunk_text = whole_text[start:end]
                        
                        # Setăm limba în prompt în funcție de selecție (doar numele limbii)
                        lang_name = selected_lang_label.split(" ")[1] 
                        header = PROMPT_INTRO.format(part=i+1, total=num_chunks, lang=lang_name)
                        final_block = header + chunk_text
                        
                        # DESIGN CERUT: Doar buton copy, ascuns textul
                        # Folosim st.expander închis implicit
                        with st.expander(f"📋 COPIAZĂ PARTEA {i+1} (Click aici)", expanded=False):
                            st.caption("Apasă iconița de 'Copy' din colțul dreapta-sus al chenarului negru 👇")
                            # st.code este singura metodă nativă Streamlit care oferă buton de copy
                            st.code(final_block, language="text")

                try: os.remove(filename)
                except: pass

            else:
                status.error(f"❌ Nu am găsit subtitrări pentru limba selectată ({selected_lang_label}).")
                
        except Exception as e:
            status.error(f"Eroare: {str(e)}")
