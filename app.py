import streamlit as st
# Importăm întregul modul mai întâi
import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import re

st.set_page_config(page_title="YouTube Transcript", page_icon="📜")
st.title("📹 YouTube la Text")

# Verificăm dacă instalarea a reușit acum
try:
    test = YouTubeTranscriptApi.get_transcript
except AttributeError:
    st.error("Eroare critică: Librăria s-a instalat greșit pe server.")
    st.info("Soluție: Modifică requirements.txt și schimbă versiunea (ex: 0.6.1)")
    st.stop()

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

if st.button("Extrage"):
    if url:
        vid_id = get_video_id(url)
        if vid_id:
            try:
                # Obținem transcriptul
                transcript = YouTubeTranscriptApi.get_transcript(vid_id, languages=['ro', 'en'])
                
                # Formatăm textul
                formatter = TextFormatter()
                text = formatter.format_transcript(transcript)
                
                st.success("Gata!")
                st.code(text, language=None)
                
            except Exception as e:
                st.error("Nu am putut extrage textul.")
                st.warning(f"Motiv: {e}")
                # Unele video-uri chiar nu au subtitrări, nu e vina codului
        else:
            st.warning("Link invalid.")
            
