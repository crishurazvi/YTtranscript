import streamlit as st
import re

# Configurare
st.set_page_config(page_title="YouTube Text", page_icon="📝")
st.title("📝 YouTube la Text")

# --- ZONA DE DIAGNOSTICARE ---
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    # Testăm dacă funcția există
    if not hasattr(YouTubeTranscriptApi, 'get_transcript'):
        raise ImportError("Funcția get_transcript lipsește! Librărie coruptă.")
except Exception as e:
    st.error("⛔ EROARE CRITICĂ DE INSTALARE")
    st.info("Te rog șterge aplicația de pe Streamlit și creeaz-o din nou (Delete & New App).")
    st.stop()
# -----------------------------

# Funcție extragere ID
def get_video_id(url):
    if not url: return None
    patterns = [r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})']
    for pattern in patterns:
        match = re.search(pattern, url)
        if match: return match.group(1)
    return None

url = st.text_input("Lipește Link-ul YouTube:")

if st.button("Extrage"):
    if not url:
        st.warning("Pune un link.")
    else:
        video_id = get_video_id(url)
        if not video_id:
            st.error("Link invalid.")
        else:
            try:
                # Încercăm să luăm transcriptul
                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                
                # Dacă reușim, îl afișăm simplu
                text = " ".join([x['text'] for x in transcript])
                st.success("✅ Succes!")
                st.text_area("Transcript:", text, height=300)
                
            except Exception as e:
                # Aici prindem blocajul YouTube
                st.error("Nu am putut extrage textul.")
                
                err_msg = str(e)
                if "Subtitles are disabled" in err_msg:
                    st.warning("🔒 BLOCAJ YOUTUBE DETECTAT")
                    st.write("Acest video (ex: BMW review) este restricționat de YouTube pentru servere (roboți).")
                    st.write("**Soluție:** Încearcă cu un alt video (știri, tutoriale) pentru a confirma că aplicația merge.")
                else:
                    st.code(err_msg)
                    
