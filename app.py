import streamlit as st
import yt_dlp
import os
import glob
import math

# --- CONFIGURARE PAGINĂ ---
st.set_page_config(page_title="Splitter Transcript", page_icon="✂️")
st.title("✂️ YouTube Splitter pentru AI")
st.info("Această aplicație împarte transcriptul în bucăți mici, ca să le poți copia pe rând în ChatGPT/Gemini fără să blochezi clipboard-ul telefonului.")

# --- PROMPT AI ---
PROMPT_INTRO = """
Ești un asistent expert. Te rog să analizezi acest transcript (PARTEA {part} din {total}) și să aștepți următoarea parte.
Dacă aceasta este ultima parte, te rog să îmi oferi în limba ROMÂNĂ:
1. REZUMAT EXECUTIV (max 3 fraze).
2. PUNCTELE CHEIE (5-7 idei esențiale).
3. CONCLUZIE PRACTICĂ.

Iată textul:
--------------------------------------------------
"""

# Configurare URL
url = st.text_input("Lipește Link-ul YouTube:")
CHUNK_SIZE = 4000 # Limita sigură pentru Android

if st.button("Extrage și Împarte"):
    if not url:
        st.warning("Pune un link!")
    else:
        status = st.empty()
        status.info("⏳ Descarc subtitrarea...")
        
        # Configurare yt-dlp
        options = {
            'skip_download': True,
            'writeautomaticsub': True,
            'writesubtitles': True,
            'subtitleslangs': ['en'],
            'outtmpl': 'temp_stream',
            'quiet': True,
            'no_warnings': True
        }

        try:
            # Curățenie
            for f in glob.glob("temp_stream*"): 
                try: os.remove(f)
                except: pass

            # Descărcare
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([url])

            # Procesare
            files = glob.glob("temp_stream*.vtt")
            
            if files:
                filename = files[0]
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Curățare text
                full_text_list = []
                seen = set()
                for line in lines:
                    line = line.strip()
                    if "-->" in line or line == "WEBVTT" or not line: continue
                    if line.startswith("<") and line.endswith(">"): continue
                    if "<" in line and ">" in line:
                        import re
                        line = re.sub(r'<[^>]+>', '', line)
                    if line in seen: continue
                    seen.add(line)
                    full_text_list.append(line)

                whole_text = " ".join(full_text_list)
                total_chars = len(whole_text)
                
                # Calcul bucăți
                num_chunks = math.ceil(total_chars / CHUNK_SIZE)
                
                status.success(f"✅ Gata! Textul are {total_chars} caractere. L-am împărțit în {num_chunks} bucăți.")
                
                # --- AFIȘARE BUCĂȚI ---
                st.markdown("---")
                
                for i in range(num_chunks):
                    start = i * CHUNK_SIZE
                    end = start + CHUNK_SIZE
                    chunk_text = whole_text[start:end]
                    
                    # Creăm header-ul pentru AI
                    header = PROMPT_INTRO.format(part=i+1, total=num_chunks)
                    final_block = header + chunk_text
                    
                    # Afișăm titlul și blocul de cod
                    st.subheader(f"🔹 Bucata {i+1} din {num_chunks}")
                    st.caption("Apasă butonul mic de 'Copy' din dreapta-sus al blocului negru:")
                    
                    # AICI E CHEIA: st.code are buton de copy integrat
                    st.code(final_block, language=None)
                    
                    st.markdown("---") # Linie separatoare

                # Curățenie finală
                os.remove(filename)

            else:
                status.error("Nu am găsit subtitrări în engleză.")
                
        except Exception as e:
            status.error(f"Eroare: {str(e)}")
            if "429" in str(e):
                st.error("Serverul a fost blocat temporar de YouTube. Încearcă mai târziu.")
                
