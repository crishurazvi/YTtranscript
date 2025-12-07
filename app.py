import streamlit as st
import sys
import os

st.title("🕵️ Investigator Erori")

try:
    import youtube_transcript_api
    st.write("### 1. Unde crede Python că este librăria?")
    st.code(youtube_transcript_api.__file__)
    
    st.write("### 2. Ce conține folderul curent?")
    st.code(os.listdir('.'))

    from youtube_transcript_api import YouTubeTranscriptApi
    st.write("### 3. Test Import Clasă")
    st.success("Clasa a fost importată.")
    
    if hasattr(YouTubeTranscriptApi, 'get_transcript'):
        st.success("✅ Funcția 'get_transcript' EXISTĂ! Totul ar trebui să meargă.")
    else:
        st.error("❌ Funcția 'get_transcript' LIPSEȘTE din clasă.")
        st.warning("Asta înseamnă că încarci un fișier local care are același nume, dar e gol sau incomplet.")

except Exception as e:
    st.error(f"Eroare fatală la import: {e}")
    
