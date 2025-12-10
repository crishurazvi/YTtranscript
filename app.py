import streamlit as st
import yt_dlp
import os
import glob
import math

# --- CONFIGURARE PAGINĂ ---
st.set_page_config(page_title="Splitter Transcript", page_icon="✂️")
st.title("✂️ YouTube Splitter")

# --- CONTROL MĂRIME (NOU) ---
# Adăugăm un slider ca să alegi tu cât de mari să fie bucățile
st.write("🔧 **Setări:**")
CHUNK_SIZE = st.slider(
    "Câte caractere să aibă o bucată?", 
    min_value=2000, 
    max_value=30000, 
    value=15000, 
    step=1000,
    help="15.000 este ideal pentru ChatGPT/Gemini. Dacă ai un telefon mai vechi, scade la 5.000."
)

# --- PROMPT AI ---
PROMPT_INTRO = """
Acționează ca un analist de conținut expert.

Input: transcriptul complet al unui videoclip YouTube (în orice limbă).

Obiectivele tale:
1. Tradu tot textul în română, păstrând sensul original.
2. Reorganizează informația într-o structură clară și didactică.
3. Păstrează toate detaliile importante; nu elimina idei esențiale.
4. Nu crea un rezumat scurtat excesiv — vreau în continuare informația completă, dar ordonată.
5. Elimină repetițiile, expresiile de umplutură și dezordinea specifică vorbirii spontane.
6. Grupați ideile logic: concepte, exemple, explicații, eventual pași sau recomandări.
7. Nu adăuga opinii personale.

Output:
1. **Versiunea curată și tradusă în română**, reorganizată logic.
2. **Structura pe secțiuni** (ex.: Introducere, Idee 1, Idee 2, Demonstrații, Concluzie).
3. **Puncte cheie** (dar nu un rezumat excesiv, doar extragerea esențialului).
4. **Conexiuni sau clarificări** dacă transcriptul este haotic — fără invenții, doar explicații ce reies din text.

Scop: să pot „consuma” tot videoclipul în câteva minute, cu fidelitate maximă, dar fără zgomot și fără să pierd timp pe YouTube.

Iată textul:
--------------------------------------------------
"""

url = st.text_input("Lipește Link-ul YouTube:")

if st.button("Extrage Transcriptul"):
    if not url:
        st.warning("Pune un link!")
    else:
        status = st.empty()
        status.info("⏳ Lucrez...")
        
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
            for f in glob.glob("temp_stream*"): 
                try: os.remove(f)
                except: pass

            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([url])

            files = glob.glob("temp_stream*.vtt")
            
            if files:
                filename = files[0]
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
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
                
                # Calculăm bucățile folosind valoarea din Slider
                num_chunks = math.ceil(total_chars / CHUNK_SIZE)
                
                status.success(f"✅ Gata! {total_chars} caractere împărțite în doar {num_chunks} bucăți.")
                
                st.markdown("---")
                
                for i in range(num_chunks):
                    start = i * CHUNK_SIZE
                    end = start + CHUNK_SIZE
                    chunk_text = whole_text[start:end]
                    
                    header = PROMPT_INTRO.format(part=i+1, total=num_chunks)
                    final_block = header + chunk_text
                    
                    st.subheader(f"🔹 Partea {i+1} din {num_chunks}")
                    st.caption("Apasă iconița de 'Copy' din colțul dreapta-sus al chenarului:")
                    st.code(final_block, language=None)
                    st.markdown("---")

                os.remove(filename)

            else:
                status.error("Nu am găsit subtitrări în engleză.")
                
        except Exception as e:
            status.error(f"Eroare: {str(e)}")
