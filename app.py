import streamlit as st
import yt_dlp
import os
import glob
import math
import re

# --- 1. CONFIGURARE PAGINĂ & DESIGN NEON ---
st.set_page_config(page_title="Neon Splitter", page_icon="⚡", layout="centered")

# CSS pentru stilul Neon Cyberpunk
st.markdown("""
    <style>
        /* Fundal general */
        .stApp {
            background-color: #0e1117;
            color: #ffffff;
        }
        
        /* Titluri cu efect de neon */
        h1 {
            color: #00f2ff !important;
            text-shadow: 0 0 10px #00f2ff, 0 0 20px #00f2ff;
            font-family: 'Courier New', Courier, monospace;
        }
        
        /* Input text */
        .stTextInput > div > div > input {
            background-color: #1c1f26;
            color: #00f2ff;
            border: 1px solid #00f2ff;
            border-radius: 5px;
        }
        
        /* Butonul Principal */
        .stButton > button {
            background-color: transparent;
            color: #ff00ff;
            border: 2px solid #ff00ff;
            border-radius: 8px;
            font-weight: bold;
            transition: all 0.3s ease;
            width: 100%;
        }
        .stButton > button:hover {
            background-color: #ff00ff;
            color: white;
            box-shadow: 0 0 15px #ff00ff, 0 0 30px #ff00ff;
        }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #111;
            border-right: 1px solid #333;
        }
        
        /* Code blocks styling */
        .stCode {
            border: 1px solid #333;
            border-left: 5px solid #00f2ff;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. HEADER ---
st.title("⚡ Neon YouTube Splitter")
st.markdown("Extrage transcriptul, împarte-l pentru AI și domină informația.")

# --- 3. SIDEBAR (SETĂRI) ---
with st.sidebar:
    st.header("⚙️ Configurare")
    
    # Selector Limbă (NOU)
    lang_options = {
        "Română": "ro",
        "Engleză": "en",
        "Franceză": "fr",
        "Spaniolă": "es",
        "Germană": "de",
        "Rusă": "ru",
        "Italiană": "it"
    }
    selected_lang_label = st.selectbox("Limba Video/Subtitrare:", list(lang_options.keys()))
    selected_lang_code = lang_options[selected_lang_label]
    
    st.write("---")
    
    # Slider Mărime
    CHUNK_SIZE = st.slider(
        "Caractere per bucată:", 
        min_value=2000, 
        max_value=30000, 
        value=15000, 
        step=1000,
        help="20.000 e ok pentru GPT-4. Pentru modele mai slabe, folosește 5-10.000."
    )

# --- 4. PROMPT AI ---
# Am adăugat {part} și {total} în text pentru a funcționa formatarea din cod
PROMPT_INTRO = """
Rol: Ești un analist de conținut expert și un traducător profesionist.
Context: Aceasta este partea {part} din {total} a transcriptului.

Sarcina:
1. Analizează textul furnizat mai jos.
2. Dacă textul este în altă limbă decât Româna, tradu-l. Dacă este deja în Română, corectează gramatica și fluidizează exprimarea.
3. Extrage ideile principale, cifrele, argumentele și exemplele concrete.
4. Elimină umplutura (intro, like & share, glume proaste).

Formatare:
- Folosește titluri H2/H3.
- Folosește Bullet Points.
- Îngroșă (Bold) conceptele cheie.

Transcriptul brut este:
--------------------------------------------------
"""

# --- 5. INTERFAȚA PRINCIPALĂ ---
url = st.text_input("Lipește Link-ul YouTube aici:")

if st.button("🚀 EXTRAGE ȘI PROCESEAZĂ"):
    if not url:
        st.warning("⚠️ Te rog pune un link valid!")
    else:
        status = st.empty()
        status.info("📡 Scanez matricea (Descarc subtitrarea)...")
        
        # Configurare yt-dlp dinamică în funcție de limba aleasă
        options = {
            'skip_download': True,
            'writeautomaticsub': True,  # Încearcă subtitrări auto-generate
            'writesubtitles': True,     # Încearcă subtitrări manuale
            'subtitleslangs': [selected_lang_code], # Folosește limba selectată
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

            # Căutare fișier rezultat (poate fi .vtt, .ro.vtt, .en.vtt etc)
            files = glob.glob("temp_stream*.vtt")
            
            if files:
                filename = files[0]
                status.info(f"💾 Procesez fișierul: {filename}...")
                
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Curățare VTT
                full_text_list = []
                seen = set()
                for line in lines:
                    line = line.strip()
                    # Ignorăm timestamp-uri, header VTT, linii goale
                    if "-->" in line or line == "WEBVTT" or not line: continue
                    if line.startswith("<") and line.endswith(">"): continue # Style tags lines
                    
                    # Curățăm tag-uri inline gen <c.colorE5E5E5>
                    if "<" in line and ">" in line:
                        line = re.sub(r'<[^>]+>', '', line)
                    
                    # Eliminăm duplicatele consecutive
                    if line in seen: continue
                    seen.add(line)
                    full_text_list.append(line)

                whole_text = " ".join(full_text_list)
                
                # Verificare dacă s-a extras ceva
                if len(whole_text) < 50:
                    status.error("❌ Subtitrarea găsită pare goală sau invalidă.")
                else:
                    total_chars = len(whole_text)
                    num_chunks = math.ceil(total_chars / CHUNK_SIZE)
                    
                    status.success(f"✅ Gata! {total_chars} caractere împărțite în {num_chunks} bucăți.")
                    st.progress(100)
                    
                    st.markdown("---")
                    
                    # Afișare bucăți
                    for i in range(num_chunks):
                        start = i * CHUNK_SIZE
                        end = start + CHUNK_SIZE
                        chunk_text = whole_text[start:end]
                        
                        # Formatăm promptul cu numărul părții
                        header = PROMPT_INTRO.format(part=i+1, total=num_chunks)
                        final_block = header + chunk_text
                        
                        st.subheader(f"🔹 Partea {i+1} / {num_chunks}")
                        st.caption("Copy-paste în ChatGPT / Claude / Gemini:")
                        st.code(final_block, language="text")
                        st.markdown("---")

                # Ștergere fișier temporar
                try: os.remove(filename)
                except: pass

            else:
                status.error(f"❌ Nu am găsit subtitrări pentru limba: {selected_lang_label} ({selected_lang_code}). Încearcă altă limbă din meniu.")
                
        except Exception as e:
            status.error(f"Eroare critică: {str(e)}")
