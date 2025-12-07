import streamlit as st
import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

st.set_page_config(page_title="YouTube Grabber", page_icon="📝")
st.title("📝 YouTube la Text")

def get_video_id(url):
    if not url: return None
    # Regex imbunatatit pentru a prinde toate formatele de link
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'(?:shorts\/)([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

url = st.text_input("Lipește Link-ul YouTube:")

if st.button("Extrage"):
    if url:
        video_id = get_video_id(url)
        if video_id:
            try:
                # STRATEGIA 1: Încercare directă (cea mai robustă)
                # Nu mai listăm transcripturile, ci cerem direct orice există.
                # Asta ocolește bug-ul de "listare goală".
                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                
                # Dacă ajungem aici, avem text!
                formatter = TextFormatter()
                text = formatter.format_transcript(transcript)
                
                st.success("✅ Transcript extras!")
                st.code(text, language=None)
                
            except Exception as e:
                # Dacă Strategia 1 eșuează, încercăm Strategia 2 (Listare manuală)
                try:
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    # Încercăm să luăm primul disponibil, oricare ar fi el
                    t = transcript_list.find_transcript(['en', 'ro', 'en-US']) 
                    text = formatter.format_transcript(t.fetch())
                    st.success("✅ Transcript extras (Metoda 2)!")
                    st.code(text, language=None)
                except Exception as e2:
                    st.error("Nu am reușit să extragem textul.")
                    st.warning("De ce se întâmplă asta?")
                    st.write("""
                    Deși pe telefon vezi transcriptul, YouTube îl blochează pentru servere în două situații:
                    1. **Restricție de vârstă:** Dacă video-ul conține condus agresiv sau limbaj licențios, YouTube cere login. Serverul nu e logat.
                    2. **Cookie Consent (Europa):** Serverul primește pop-up-ul de "Accept Cookies" și nu poate trece de el.
                    """)
                    st.info(f"Eroare tehnică: {e}")
        else:
            st.error("Link invalid.")
            
