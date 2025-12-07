import streamlit as st
# Importăm direct librăria, nu doar clasa, pentru a evita confuziile
import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import re

st.set_page_config(page_title="YouTube Transcript Grabber", page_icon="📜")

st.title("📹 YouTube la Text")

# --- DEBUG INFO (Apare doar dacă e eroare) ---
# Verificăm ce versiune vede Python
try:
    version = youtube_transcript_api.__version__
except:
    version = "Necunoscută"
# ---------------------------------------------

def get_video_id(url):
    video_id = None
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

url = st.text_input("Lipește Link-ul YouTube aici:")

if st.button("Extrage Transcriptul"):
    if url:
        video_id = get_video_id(url)
        
        if video_id:
            try:
                # Metoda 1: Încercăm metoda standard
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ro', 'en'])
                
                formatter = TextFormatter()
                text_formatted = formatter.format_transcript(transcript)
                
                st.success("Transcript extras cu succes!")
                st.code(text_formatted, language=None)
                
            except Exception as e:
                # Afișăm eroarea detaliată pentru debugging
                st.error("A apărut o eroare la extragere.")
                st.warning(f"Detalii eroare: {e}")
                st.info(f"Info Debug: Versiune Librărie: {version}")
                st.info("Dacă eroarea spune 'no attribute get_transcript', verifică să nu ai un fișier numit 'youtube_transcript_api.py' în GitHub.")
        else:
            st.warning("Link-ul nu pare valid.")
    else:
        st.warning("Te rog introdu un link.")
        
