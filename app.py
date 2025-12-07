import yt_dlp
import os
import glob
import math

# --- CONFIGURARE PROMPT AI ---
PROMPT_INTRO = """
Ești un asistent expert. Te rog să analizezi acest transcript (PARTEA {part} din {total}) și să aștepți următoarea parte.
Dacă aceasta este ultima parte, te rog să îmi oferi în limba ROMÂNĂ:
1. REZUMAT EXECUTIV (max 3 fraze).
2. PUNCTELE CHEIE (5-7 idei esențiale).
3. CONCLUZIE PRACTICĂ.

Iată textul:
--------------------------------------------------
"""

print("--- YOUTUBE SPLITTER (yt-dlp) ---")
url = input("Lipește link-ul: ")

# Limita de caractere per bucată (Android clipboard safe)
CHUNK_SIZE = 4000 

options = {
    'skip_download': True,
    'writeautomaticsub': True,
    'writesubtitles': True,
    'subtitleslangs': ['en'],
    'outtmpl': 'temp_sub',
    'quiet': True,
    'no_warnings': True
}

try:
    print("\n[1/3] ⏳ Descarc subtitrarea...")
    
    for f in glob.glob("temp_sub*"): 
        try: os.remove(f)
        except: pass

    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])

    print("[2/3] ✅ Procesez textul...")

    files = glob.glob("temp_sub*.vtt")
    
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

        # Unim tot textul curat
        whole_text = " ".join(full_text_list)
        total_chars = len(whole_text)
        
        # Calculăm câte bucăți sunt necesare
        num_chunks = math.ceil(total_chars / CHUNK_SIZE)
        
        print(f"\n[INFO] Text total: {total_chars} caractere.")
        print(f"[INFO] Voi împărți în {num_chunks} bucăți pentru copiere ușoară.\n")
        
        # Împărțim și afișăm
        for i in range(num_chunks):
            start = i * CHUNK_SIZE
            end = start + CHUNK_SIZE
            chunk_text = whole_text[start:end]
            
            # Construim prompt-ul specific pentru fiecare bucată
            header = PROMPT_INTRO.format(part=i+1, total=num_chunks)
            final_block = header + chunk_text
            
            print(f"\n🔵 --- BUCATA {i+1} din {num_chunks} --- (Copiaza mai jos)")
            print("="*20)
            print(final_block)
            print("="*20)
            
            if i < num_chunks - 1:
                input("\n👉 Apasă ENTER pentru a afișa următoarea bucată...")
        
        print("\n✅ GATA! Ai copiat toate bucățile.")
        os.remove(filename)
        
    else:
        print("\n❌ EROARE: Nu am găsit subtitrări.")

except Exception as e:
    print(f"\n❌ EROARE: {e}")
    
