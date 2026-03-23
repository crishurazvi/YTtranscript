import streamlit as st
import yt_dlp
import os
import glob
import math
import re

# --- 1. CONFIGURARE PAGINĂ & DARK MODE FORȚAT ---
st.set_page_config(page_title="Dark Transcript", page_icon="☕", layout="centered")

# CSS Minimalist, Ultra-Rapid și Complet Negru
st.markdown("""
    <style>
        /* Ascundem meniul Streamlit pentru un aspect de aplicație curată */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Tema True Black */
        .stApp {
            background-color: #000000;
            color: #E0E0E0;
        }
        
        /* Accente de culoare */
        h1, h2, h3, h4 { color: #D4A373 !important; font-weight: 400 !important; }
        
        /* Căsuțe de input mai elegante */
        .stTextInput > div > div > input {
            background-color: #111111;
            color: #FFF;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 15px;
            font-size: 16px;
        }
        .stTextInput > div > div > input:focus {
            border-color: #D4A373;
            box-shadow: none;
        }
        
        /* Selectoare și Slidere */
        .stSelectbox > div > div > div { background-color: #111111; color: #FFF; border: 1px solid #333; }
        
        /* Cod blocks (pentru butonul de copy) */
        .stCode {
            background-color: #111111 !important;
            border: 1px solid #333 !important;
            border-left: 3px solid #BC6C25 !important;
            border-radius: 8px;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. HEADER ---
st.title("☕ Dark Roast Transcript")
st.caption("⚡ Paste + Enter")

# --- 3. FUNCȚIE CACHED PENTRU VITEZĂ MAXIMĂ ---
# Dacă schimbi setările, nu mai descarcă de pe net, folosește memoria RAM!
@st.cache_data(show_spinner=False)
def extrage_transcript(url, lang_code):
    options = {
        'skip_download': True,
        'writeautomaticsub': True,
        'writesubtitles': True,
        'subtitleslangs': [lang_code],
        'outtmpl': 'temp_stream',
        'quiet': True,
        'no_warnings': True
    }
    
    # Curățare preventivă
    for f in glob.glob("temp_stream*"): 
        try: os.remove(f)
        except: pass

    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])

    files = glob.glob("temp_stream*.vtt")
    if not files:
        return None

    filename = files[0]
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    # Procesare ultra-rapidă text
    seen = set()
    full_text_list = []
    for line in lines:
        line = line.strip()
        if not line or "-->" in line or line == "WEBVTT": continue
        if line.startswith("<") and line.endswith(">"): continue
        if "<" in line and ">" in line:
            line = re.sub(r'<[^>]+>', '', line)
        if line not in seen:
            seen.add(line)
            full_text_list.append(line)

    try: os.remove(filename)
    except: pass

    return " ".join(full_text_list)

# --- 4. CONTROALE & INPUT ---
col1, col2 = st.columns([1, 2])
with col1:
    lang_options = {"🇬🇧 EN": "en", "🇷🇴 RO": "ro", "🇫🇷 FR": "fr", "🇪🇸 ES": "es", "🇩🇪 DE": "de"}
    selected_lang = st.selectbox("Limbă", list(lang_options.keys()), index=0, label_visibility="collapsed")
    lang_code = lang_options[selected_lang]

with col2:
    CHUNK_SIZE = st.slider("Caractere", 2000, 30000, 15000, 1000, label_visibility="collapsed")

# Input URL care declanșează automat procesul
url = st.text_input("Link YouTube", label_visibility="collapsed", placeholder="Paste + Enter...")

# --- 5. LOGICA DE PROCESARE (AUTO-RUN) ---
PROMPT_INTRO = """
Rol: Ești un Expert în analiză de conținut video youtube.
Sarcina: Tradu în limba română și restructurează informatia ca un articol web usor de citit, formatare markdown + emoji. 
fara rezumare excessive. 
NU folosi excesiv bullet points 
        (Partea {part}/{total}). 
        scopul este ca să parcurg informația citind în loc să mă uit la video

Transcript de procesat:
--------------------------------------------------
"""

if url:
    with st.spinner("☕ Se prepară transcriptul..."):
        try:
            text_rezultat = extrage_transcript(url, lang_code)
            
            if text_rezultat and len(text_rezultat) > 50:
                num_chunks = math.ceil(len(text_rezultat) / CHUNK_SIZE)
                
                st.success(f"✅ Descărcat! Împărțit în **{num_chunks}** secțiuni.")
                
                # Afișare directă, FĂRĂ tab-uri (expander). 
                # Dai scroll și copiezi din butonul nativ colț-dreapta.
                for i in range(num_chunks):
                    start = i * CHUNK_SIZE
                    end = start + CHUNK_SIZE
                    chunk_text = text_rezultat[start:end]
                    
                    header = PROMPT_INTRO.format(part=i+1, total=num_chunks)
                    
                    st.markdown(f"**Partea {i+1} / {num_chunks}**")
                    st.code(header + chunk_text, language="text")
                    
            else:
                st.error("❌ Nu am găsit subtitrări sau fișierul este gol.")
                
        except Exception as e:
            st.error(f"Eroare: {str(e)}")
