import streamlit as st
import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

st.set_page_config(page_title="YouTube Transcript", page_icon="📜")
st.title("📹 YouTube la Text (Auto-Generat)")

def get_video_id(url):
    if not url: return None
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

url = st.text_input("Lipește Link-ul YouTube:")

if st.button("Extrage Transcriptul"):
    if url:
        video_id = get_video_id(url)
        if video_id:
            try:
                # PASUL 1: Obținem lista tuturor transcripturilor disponibile
                # Aceasta include și cele "Auto-generated"
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                
                final_transcript = None
                
                # PASUL 2: Încercăm să găsim unul generat automat sau manual
                # Prioritizăm Româna și Engleza, dar acceptăm și altele
                try:
                    # Căutăm manual sau automat în RO sau EN
                    transcript = transcript_list.find_transcript(['ro', 'en', 'en-US', 'en-GB'])
                    final_transcript = transcript.fetch()
                    st.success(f"Am găsit transcript în limba: {transcript.language}")
                except:
                    # Dacă nu găsim specific, luăm PRIMUL disponibil (oricare ar fi el)
                    # Asta rezolvă problema cu "Auto-generated" care au coduri ciudate
                    st.warning("Nu am găsit RO/EN specific, încercăm orice versiune auto-generată disponibilă...")
                    for t in transcript_list:
                        final_transcript = t.fetch()
                        st.success(f"Am extras transcriptul auto-generat: {t.language} ({t.language_code})")
                        break
                
                # PASUL 3: Afișăm textul
                if final_transcript:
                    formatter = TextFormatter()
                    text_formatted = formatter.format_transcript(final_transcript)
                    st.code(text_formatted, language=None)
                else:
                    st.error("Nu s-a putut extrage niciun text.")

            except Exception as e:
                # Aici prindem cazul în care CHIAR nu există nimic
                st.error("Eroare: Acest video nu are niciun fel de transcript disponibil.")
                st.info("Posibile cauze:")
                st.write("1. Videoclipul este prea nou și YouTube încă nu a generat textul.")
                st.write("2. Este un videoclip muzical fără versuri setate.")
                st.write("3. Creatorul a dezactivat complet subtitrările/CC.")
                st.warning(f"Detalii tehnice: {e}")
        else:
            st.warning("Link invalid.")
        
