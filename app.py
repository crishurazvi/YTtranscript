import streamlit as st
import yt_dlp
import os
import glob

# --- CONFIGURARE PAGINĂ ---
st.set_page_config(page_title="YouTube to AI", page_icon="🤖")
st.title("🤖 YouTube Transcript -> AI Prompt")
st.write("Extrage transcriptul în engleză și adaugă instrucțiuni pentru rezumat.")

# --- CONFIGURARE PROMPT AI ---
PROMPT_AI = """
Ești un asistent expert. Te rog să analizezi următorul transcript (în limba engleză) și să îmi oferi în limba ROMÂNĂ:
1. REZUMAT EXECUTIV (max 3 fraze).
2. PUNCTELE CHEIE (5-7 idei esențiale).
3. CONCLUZIE PRACTICĂ.

Iată transcriptul:
--------------------------------------------------
"""

# Input URL
url = st.text_input("Lipește Link-ul YouTube:")

# Buton
if st.button("Generează Prompt-ul"):
    if not url:
        st.warning("Te rog introdu un link.")
    else:
        # Configurare yt-dlp
        options = {
            'skip_download': True,       # Nu descărcăm video
            'writeautomaticsub': True,   # Subtitrări auto
            'writesubtitles': True,      # Subtitrări manuale
            'subtitleslangs': ['en'],    # Doar engleză
            'outtmpl': 'temp_sub',       # Nume fișier temporar
            'quiet': True,
            'no_warnings': True
        }

        status_area = st.empty() # Zona pentru mesaje de status
        
        try:
            status_area.info("⏳ Contactez YouTube... (poate dura câteva secunde)")
            
            # 1. Curățăm fișiere vechi
            for f in glob.glob("temp_sub*"): 
                try: os.remove(f)
                except: pass

            # 2. Descărcăm
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([url])

            # 3. Procesăm fișierul
            files = glob.glob("temp_sub*.vtt")
            
            if files:
                filename = files[0]
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                full_text = []
                seen = set()
                
                for line in lines:
                    line = line.strip()
                    # Filtrare gunoi VTT
                    if "-->" in line or line == "WEBVTT" or not line: continue
                    if line.startswith("<") and line.endswith(">"): continue
                    # Filtrare etichete timp inline <00:00:01>
                    if "<" in line and ">" in line:
                        import re
                        line = re.sub(r'<[^>]+>', '', line)
                        
                    if line in seen: continue
                    seen.add(line)
                    full_text.append(line)

                # 4. Asamblăm rezultatul
                final_output = PROMPT_AI + " ".join(full_text)
                
                status_area.success("✅ Gata! Copiază textul de mai jos:")
                
                # Afișăm în zona de cod cu buton de copy
                st.code(final_output, language=None)
                
                # Ștergem fișierul temporar
                os.remove(filename)
                
            else:
                status_area.error("❌ Nu am găsit subtitrări în engleză pentru acest video.")

        except Exception as e:
            err_msg = str(e)
            if "Too Many Requests" in err_msg or "429" in err_msg:
                status_area.error("⛔ Blocaj YouTube (429).")
                st.warning("Serverul Streamlit a fost blocat temporar de YouTube. Încearcă din nou peste 10 minute sau folosește Pydroid pe telefon.")
            else:
                status_area.error(f"Eroare: {err_msg}")
                
