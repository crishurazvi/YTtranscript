import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import re

# Configurare pagină
st.set_page_config(page_title="YouTube Transcript Grabber", page_icon="📜")

st.title("📹 YouTube la Text")
st.write("Lipește linkul și obține textul imediat.")

# Funcție pentru a extrage ID-ul video-ului din link
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

# Input utilizator
url = st.text_input("Lipește Link-ul YouTube aici:")

if st.button("Extrage Transcriptul"):
    if url:
        video_id = get_video_id(url)
        
        if video_id:
            try:
                # Încercăm să luăm transcriptul (preferabil în română, apoi engleză)
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ro', 'en'])
                
                # Formatăm textul frumos (fără timpi)
                formatter = TextFormatter()
                text_formatted = formatter.format_transcript(transcript)
                
                st.success("Transcript extras cu succes!")
                
                # Afișăm textul într-o zonă de cod pentru copiere ușoară
                # Streamlit are un buton de "copy" integrat în blocurile de cod
                st.code(text_formatted, language=None)
                
                st.info("Sfat: Apasă butonul mic de 'Copy' din colțul dreapta-sus al blocului de text de mai sus.")
                
            except Exception as e:
                st.error(f"Eroare: Nu am găsit subtitrări sau video-ul este restricționat. ({e})")
        else:
            st.warning("Link-ul nu pare valid.")
    else:
        st.warning("Te rog introdu un link.")