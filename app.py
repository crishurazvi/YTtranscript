import streamlit as st
import yt_dlp
import os
import glob
import math
import re

# --- 1. SETĂRI PAGINĂ (ULTRA MINIMALIST) ---
st.set_page_config(page_title="Auto Transcript", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
        /* Ascundem tot ce ține de Streamlit (Meniu, Footer, Header alb) */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Fundal Complet Negru */
        .stApp { background-color: #000000; color: #FFFFFF; }
        
        /* Căsuța de Input (Mare și centrală) */
        .stTextInput > div > div > input {
            background-color: #111111;
            color: #FFFFFF;
            border: 2px solid #333333;
            border-radius: 12px;
            padding: 18px;
            font-size: 18px;
            transition: 0.3s;
        }
        .stTextInput > div > div > input:focus {
            border-color: #BC6C25; /* Portocaliu la focus */
            box-shadow: none;
        }
        
        /* Design Tab-uri (fără scroll, ca niște butoane sus) */
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #1A1A1A;
            border-radius: 6px;
            padding: 10px 20px;
            border: 1px solid #333;
        }
        .stTabs [aria-selected="true"] {
            background-color: #BC6C25 !important;
            color: #fff !important;
            border-color: #BC6C25 !important;
        }
        
        /* Zona de cod (de unde copiezi) */
        .stCode {
            background-color: #0A0A0A !important;
            border: 1px solid #333 !important;
            border-radius: 8px;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGICĂ DESCĂRCARE (FĂRĂ CACHE PT SIMPLITATE) ---
def extrage_transcript(url):
    # Setat să caute automat subtitrări în EN sau RO
    options = {
        'skip_download': True,
        'writeautomaticsub': True,
        'writesubtitles': True,
        'subtitleslangs': ['en', 'ro'], 
        'outtmpl': 'temp_stream',
        'quiet': True,
        'no_warnings': True
    }
    
    # Curățare fișiere vechi
    for f in glob.glob("temp_stream*"): 
        try: os.remove(f)
        except: pass

    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])

    files = glob.glob("temp_stream*.vtt")
    if not files: return None

    filename = files[0]
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    seen = set()
    full_text = []
    for line in lines:
        line = line.strip()
        if not line or "-->" in line or line == "WEBVTT": continue
        if line.startswith("<") and line.endswith(">"): continue
        if "<" in line and ">" in line: line = re.sub(r'<[^>]+>', '', line)
        if line not in seen:
            seen.add(line)
            full_text.append(line)

    try: os.remove(filename)
    except: pass

    return " ".join(full_text)

# --- 3. INTERFAȚA UTILIZATORULUI ---
st.markdown("<h1 style='text-align: center; color: #D4A373; margin-top: 20px;'>⚡ Paste & Copy</h1>", unsafe_allow_html=True)

# Singurul element cu care interacționezi
url = st.text_input("", placeholder="🔗 Paste Link-ul de YouTube aici și apasă ENTER...", label_visibility="collapsed")

if url:
    with st.spinner("Se procesează instant..."):
        try:
            text = extrage_transcript(url)
            
            if text and len(text) > 50:
                # Tăiere automată la mărimea ideală pt AI
                CHUNK_SIZE = 15000 
                num_chunks = math.ceil(len(text) / CHUNK_SIZE)
                
                PROMPT = "Rol: Ești analist de conținut.\nSarcina: Tradu în limba română, extrage ideile principale, ignoră reclamele. Formatează clar.\nPartea: {part} din {total}\n--------------------------------------------------\n"
                
                # CREARE TAB-URI (Aici se elimină complet scroll-ul!)
                tab_titles = [f"📋 Partea {i+1}" for i in range(num_chunks)]
                tabs = st.tabs(tab_titles)
                
                for i, tab in enumerate(tabs):
                    with tab:
                        start = i * CHUNK_SIZE
                        end = start + CHUNK_SIZE
                        chunk_text = text[start:end]
                        
                        header = PROMPT.format(part=i+1, total=num_chunks)
                        # Textul apare gata de copiat cu iconița în dreapta sus
                        st.code(header + chunk_text, language="text")
                        
            else:
                st.error("❌ Nu am putut găsi subtitrări pe acest videoclip.")
                
        except Exception as e:
            st.error("A apărut o eroare. Verifică link-ul.")
