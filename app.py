import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
import re

st.set_page_config(page_title="YouTube Text", page_icon="📝")
st.title("📝 YouTube la Text")

# --- VERIFICARE INSTALARE ---
try:
    # Verificăm dacă librăria e instalată corect
    if not hasattr(YouTubeTranscriptApi, 'get_transcript'):
        st.error("ERROARE INTERNĂ: Librăria s-a instalat greșit.")
        st.stop()
except:
    st.error("Librăria lipsește complet.")
    st.stop()
# -----------------------------

def get_video_id(url):
    if not url: return None
    patterns = [r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})']
    for pattern in patterns:
        match = re.search(pattern, url)
        if match: return match.group(1)
    return None

url = st.text_input("Lipește Link-ul YouTube:")

if st.button("Extrage"):
    video_id = get_video_id(url)
    if not video_id:
        st.error("Link invalid.")
    else:
        try:
            # Încercăm să luăm transcriptul
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            
            # Formatăm textul
            text = " ".join([x['text'] for x in transcript])
            st.success("✅ Succes!")
            st.text_area("Transcript:", text, height=400)
            
        except Exception as e:
            err = str(e)
            if "Subtitles are disabled" in err:
                st.error("🔒 BLOCAJ YOUTUBE DETECTAT")
                st.warning("""
                Deși pe telefonul tău transcriptul apare, YouTube a blocat accesul serverului nostru la acest video.
                Cauză: YouTube crede că serverul este un robot sau videoclipul are restricții geografice/de vârstă.
                """)
                st.info("SOLUȚIE TEST: Încearcă un alt video (ex: un tutorial simplu sau știri) pentru a verifica dacă aplicația merge.")
            else:
                st.error("Eroare neașteptată:")
                st.code(err)
                
