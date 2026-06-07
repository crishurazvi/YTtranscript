import streamlit as st
import yt_dlp
import os
import re
import math
import sqlite3
import tempfile
import zipfile
import io
import html
from pathlib import Path
from datetime import datetime


# ============================================================
# CONFIG
# ============================================================

APP_TITLE = "☕ Dark Roast Scholar"
APP_SUBTITLE = "YouTube transcript → clean text → AI-ready chunks → export"

DATA_DIR = Path("dark_roast_data")
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
DB_PATH = DATA_DIR / "history.sqlite"

DATA_DIR.mkdir(exist_ok=True)
TRANSCRIPTS_DIR.mkdir(exist_ok=True)


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Dark Roast Scholar",
    page_icon="☕",
    layout="centered"
)


# ============================================================
# CSS DARK MODE
# ============================================================

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .stApp {
        background-color: #000000;
        color: #E0E0E0;
    }

    h1, h2, h3, h4 {
        color: #D4A373 !important;
        font-weight: 400 !important;
    }

    .stCaption, caption {
        color: #A0A0A0 !important;
    }

    .stTextInput > div > div > input {
        background-color: #111111;
        color: #FFFFFF;
        border: 1px solid #333333;
        border-radius: 8px;
        padding: 15px;
        font-size: 16px;
    }

    .stTextInput > div > div > input:focus {
        border-color: #D4A373;
        box-shadow: none;
    }

    .stTextArea > div > div > textarea {
        background-color: #111111;
        color: #FFFFFF;
        border: 1px solid #333333;
        border-radius: 8px;
    }

    .stTextArea > div > div > textarea:focus {
        border-color: #D4A373;
        box-shadow: none;
    }

    .stSelectbox > div > div > div {
        background-color: #111111;
        color: #FFFFFF;
        border: 1px solid #333333;
    }

    .stCode {
        background-color: #111111 !important;
        border: 1px solid #333333 !important;
        border-left: 3px solid #BC6C25 !important;
        border-radius: 8px;
    }

    .streamlit-expanderHeader {
        background-color: #0A0A0A !important;
        color: #D4A373 !important;
        border-radius: 8px;
    }

    div[data-testid="stMetric"] {
        background-color: #0A0A0A;
        border: 1px solid #222222;
        padding: 12px;
        border-radius: 10px;
    }

    .video-card {
        background-color: #080808;
        border: 1px solid #222222;
        border-radius: 14px;
        padding: 14px;
        margin-bottom: 14px;
    }

    .small-muted {
        color: #999999;
        font-size: 0.9rem;
    }

    .gold {
        color: #D4A373;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# DATABASE
# ============================================================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            source_type TEXT NOT NULL,
            url TEXT,
            video_id TEXT,
            title TEXT,
            channel TEXT,
            language TEXT,
            transcript_path TEXT,
            markdown_path TEXT,
            char_count INTEGER,
            chunk_count INTEGER,
            prompt_mode TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_history(
    source_type,
    url,
    video_id,
    title,
    channel,
    language,
    transcript_text,
    markdown_text,
    char_count,
    chunk_count,
    prompt_mode
):
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    safe_id = sanitize_filename(video_id or title or f"upload_{datetime.now().timestamp()}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    txt_path = TRANSCRIPTS_DIR / f"{timestamp}_{safe_id}.txt"
    md_path = TRANSCRIPTS_DIR / f"{timestamp}_{safe_id}.md"

    txt_path.write_text(transcript_text, encoding="utf-8")
    md_path.write_text(markdown_text, encoding="utf-8")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO history (
            created_at, source_type, url, video_id, title, channel,
            language, transcript_path, markdown_path,
            char_count, chunk_count, prompt_mode
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        created_at,
        source_type,
        url,
        video_id,
        title,
        channel,
        language,
        str(txt_path),
        str(md_path),
        char_count,
        chunk_count,
        prompt_mode
    ))

    conn.commit()
    conn.close()


def get_history(limit=25):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM history
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cur.fetchall()
    conn.close()

    return rows


def find_existing_video(video_id, language):
    if not video_id:
        return None

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM history
        WHERE video_id = ? AND language = ?
        ORDER BY id DESC
        LIMIT 1
    """, (video_id, language))

    row = cur.fetchone()
    conn.close()

    return row


init_db()


# ============================================================
# UTILS
# ============================================================

def sanitize_filename(name):
    if not name:
        return "transcript"
    name = re.sub(r"[^\w\s.-]", "", name, flags=re.UNICODE)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:90] or "transcript"


def estimate_tokens(text):
    return int(len(text) / 4)


def format_duration(seconds):
    if not seconds:
        return "—"

    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    if h:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"


def extract_video_id(info):
    return info.get("id") or info.get("display_id") or ""


def clean_text_basic(text):
    text = html.unescape(text)
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def seconds_to_timestamp(seconds):
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def parse_vtt_timestamp_to_seconds(ts):
    ts = ts.strip().replace(",", ".")
    parts = ts.split(":")

    try:
        if len(parts) == 3:
            h = int(parts[0])
            m = int(parts[1])
            s = float(parts[2])
            return h * 3600 + m * 60 + s

        if len(parts) == 2:
            m = int(parts[0])
            s = float(parts[1])
            return m * 60 + s
    except Exception:
        return None

    return None


def clean_subtitle_file(content, keep_timestamps=False):
    """
    Curăță VTT/SRT/TXT.
    Elimină duplicatele consecutive, nu toate duplicatele globale.
    """

    content = content.decode("utf-8", errors="ignore") if isinstance(content, bytes) else content
    content = html.unescape(content)
    lines = content.splitlines()

    output = []
    previous_text = ""
    current_timestamp = None

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            continue

        upper = line.upper()

        if upper.startswith("WEBVTT"):
            continue

        if upper.startswith("NOTE"):
            continue

        if re.fullmatch(r"\d+", line):
            continue

        if "-->" in line:
            left = line.split("-->")[0].strip()
            seconds = parse_vtt_timestamp_to_seconds(left)
            if seconds is not None:
                current_timestamp = seconds_to_timestamp(seconds)
            continue

        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", "", line)
        line = re.sub(r"<\d{2}:\d{2}\.\d{3}>", "", line)
        line = clean_text_basic(line)

        if not line:
            continue

        if line == previous_text:
            continue

        previous_text = line

        if keep_timestamps and current_timestamp:
            output.append(f"[{current_timestamp}] {line}")
        else:
            output.append(line)

    text = " ".join(output)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = text.strip()

    return text


def split_sentences(text):
    text = clean_text_basic(text)

    protected = {
        "Dr.": "Dr§",
        "Prof.": "Prof§",
        "Mr.": "Mr§",
        "Mrs.": "Mrs§",
        "e.g.": "eg§",
        "i.e.": "ie§",
        "etc.": "etc§",
    }

    for k, v in protected.items():
        text = text.replace(k, v)

    parts = re.split(r"(?<=[.!?])\s+", text)

    restored = []
    for part in parts:
        for k, v in protected.items():
            part = part.replace(v, k)
        if part.strip():
            restored.append(part.strip())

    return restored


def chunk_text(text, chunk_size=15000, overlap=500, mode="Pe propoziții"):
    text = clean_text_basic(text)

    if len(text) <= chunk_size:
        return [text]

    chunks = []

    if mode == "Pe caractere":
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = max(end - overlap, end)
        return chunks

    if mode == "Pe paragrafe":
        units = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(units) <= 1:
            units = split_sentences(text)
    else:
        units = split_sentences(text)

    current = ""

    for unit in units:
        if not current:
            current = unit
            continue

        if len(current) + len(unit) + 1 <= chunk_size:
            current += " " + unit
        else:
            chunks.append(current.strip())

            if overlap > 0:
                overlap_text = current[-overlap:].strip()
                current = overlap_text + " " + unit
            else:
                current = unit

    if current.strip():
        chunks.append(current.strip())

    return chunks


def build_markdown_export(
    title,
    url,
    channel,
    language,
    transcript,
    chunks,
    prompt_mode,
    prompt_template
):
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = []
    md.append("---")
    md.append(f'title: "{title or "Untitled"}"')
    md.append(f'source: "{url or "local upload"}"')
    md.append(f'channel: "{channel or ""}"')
    md.append(f'language: "{language or ""}"')
    md.append(f'date: "{date_str}"')
    md.append(f'prompt_mode: "{prompt_mode}"')
    md.append("tags: [youtube, transcript, dark-roast-scholar]")
    md.append("---\n")

    md.append(f"# {title or 'Transcript'}\n")

    if url:
        md.append(f"Source: {url}\n")

    if channel:
        md.append(f"Channel: {channel}\n")

    md.append("## Transcript curat\n")
    md.append(transcript)
    md.append("\n\n---\n")

    md.append("## Prompt template\n")
    md.append("```text")
    md.append(prompt_template)
    md.append("```\n")

    md.append("## AI chunks\n")

    total = len(chunks)
    for idx, chunk in enumerate(chunks, start=1):
        try:
            header = prompt_template.format(part=idx, total=total)
        except Exception:
            header = prompt_template + f"\n\n(Partea {idx}/{total})\n"

        md.append(f"### Partea {idx}/{total}\n")
        md.append("```text")
        md.append(header + chunk)
        md.append("```\n")

    return "\n".join(md)


def build_zip_file(files_dict):
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files_dict.items():
            zf.writestr(filename, content)
    mem.seek(0)
    return mem


# ============================================================
# YOUTUBE FUNCTIONS
# ============================================================

@st.cache_data(show_spinner=False)
def get_youtube_info(url):
    opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "ignoreerrors": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return info


def collect_subtitle_languages(info):
    result = {}

    subtitles = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}

    for lang in sorted(subtitles.keys()):
        result[f"{lang} - manual"] = {"lang": lang, "type": "manual"}

    for lang in sorted(auto.keys()):
        if f"{lang} - manual" not in result:
            result[f"{lang} - auto"] = {"lang": lang, "type": "auto"}

    return result


def flatten_playlist_entries(info):
    if info.get("_type") == "playlist" and info.get("entries"):
        return [e for e in info.get("entries") if e]

    if info.get("entries") and not info.get("url"):
        return [e for e in info.get("entries") if e]

    return [info]


def get_entry_url(entry):
    webpage_url = entry.get("webpage_url")
    if webpage_url:
        return webpage_url

    url = entry.get("url")
    if url and url.startswith("http"):
        return url

    video_id = entry.get("id")
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"

    return None


@st.cache_data(show_spinner=False)
def extract_transcript_from_youtube(url, lang_code, keep_timestamps):
    with tempfile.TemporaryDirectory() as tmpdir:
        outtmpl = os.path.join(tmpdir, "subtitle")

        options = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [lang_code],
            "subtitlesformat": "vtt/srt/best",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)

        subtitle_files = []
        for ext in ("vtt", "srt"):
            subtitle_files.extend(Path(tmpdir).glob(f"subtitle*.{ext}"))

        if not subtitle_files:
            return None, info

        subtitle_file = subtitle_files[0]
        content = subtitle_file.read_text(encoding="utf-8", errors="ignore")
        cleaned = clean_subtitle_file(content, keep_timestamps=keep_timestamps)

        return cleaned, info


# ============================================================
# PROMPTS
# ============================================================

PROMPT_PRESETS = {
    "Articol română": """Rol: Ești un expert în analiză de conținut video YouTube.
Sarcină: Tradu în limba română și restructurează informația ca un articol web ușor de citit.
Stil: clar, natural, cu titluri și subtitluri.
Nu face rezumare excesivă.
Nu folosi excesiv bullet points.
Păstrează ideile importante și ordinea logică.
(Partea {part}/{total})

Transcript de procesat:
--------------------------------------------------
""",

    "Rezumat didactic": """Rol: Ești un profesor foarte bun.
Sarcină: Explică transcriptul în limba română, didactic, clar, ca pentru cineva care vrea să învețe.
Obiectiv: transformă informația într-un material de curs.
Include:
1. Explicație narativă
2. Idei-cheie
3. Concepte importante
4. Ce trebuie reținut pentru examen
Nu inventa informații în afara transcriptului.
(Partea {part}/{total})

Transcript de procesat:
--------------------------------------------------
""",

    "Curs medical": """Rol: Ești profesor universitar de medicină.
Sarcină: Transformă transcriptul într-un curs medical clar, structurat și didactic, în limba română.
Cerințe:
- păstrează fidelitatea față de transcript
- explică termenii importanți
- organizează informația logic
- nu inventa date care nu apar în transcript
- formulează ca un capitol de curs, nu ca bullet points interminabile
La final include:
1. Mesajele esențiale
2. Capcane frecvente de examen
3. Termeni medicali importanți
(Partea {part}/{total})

Transcript de procesat:
--------------------------------------------------
""",

    "Traducere fidelă": """Rol: Ești traducător specializat.
Sarcină: Tradu fidel transcriptul în limba română.
Păstrează sensul original, tonul și ordinea ideilor.
Nu rezuma.
Nu adăuga informații noi.
Corectează doar formulările incoerente produse de subtitrarea automată.
(Partea {part}/{total})

Transcript de procesat:
--------------------------------------------------
""",

    "QCM Anki": """Rol: Ești profesor și creator de întrebări pentru Anki.
Sarcină: Creează întrebări grilă în limba română pe baza transcriptului.
Format obligatoriu:
START
Basic
Front: Întrebare...
A. ...
B. ...
C. ...
D. ...
E. ...
Back: Răspuns corect: ...
Explicații:
- A: ...
- B: ...
- C: ...
- D: ...
- E: ...
Tags: youtube::transcript
END

Reguli:
- 5 variante A-E
- pot exista răspunsuri unice sau multiple
- distractori plauzibili
- explicații clare
- nu inventa informații care nu apar în transcript
(Partea {part}/{total})

Transcript de procesat:
--------------------------------------------------
""",

    "Flashcards": """Rol: Ești expert în învățare activă.
Sarcină: Creează flashcarduri clare în limba română pe baza transcriptului.
Format:
START
Basic
Front: ...
Back: ...
Tags: youtube::flashcards
END

Reguli:
- o singură idee per card
- întrebări scurte
- răspunsuri clare
- nu inventa informații care nu apar în transcript
(Partea {part}/{total})

Transcript de procesat:
--------------------------------------------------
""",

    "Obsidian note": """Rol: Ești expert în structurarea notițelor în Obsidian.
Sarcină: Transformă transcriptul într-o notiță Markdown în limba română.
Include:
# Titlu
## Ideea centrală
## Explicație
## Concepte-cheie
## Detalii importante
## Întrebări de verificare
## De reținut

Nu inventa informații în afara transcriptului.
(Partea {part}/{total})

Transcript de procesat:
--------------------------------------------------
""",

    "Custom": ""
}


# ============================================================
# HEADER
# ============================================================

st.title(APP_TITLE)
st.caption(APP_SUBTITLE)


# ============================================================
# SIDEBAR HISTORY
# ============================================================

with st.sidebar:
    st.markdown("## 📚 Istoric local")

    rows = get_history(limit=20)

    if not rows:
        st.caption("Încă nu ai transcripturi salvate.")
    else:
        for row in rows:
            title = row["title"] or "Untitled"
            created_at = row["created_at"]
            language = row["language"] or "?"
            chars = row["char_count"] or 0

            with st.expander(f"{title[:45]}"):
                st.caption(f"{created_at} · {language} · {chars:,} caractere")

                txt_path = Path(row["transcript_path"])
                md_path = Path(row["markdown_path"])

                if txt_path.exists():
                    st.download_button(
                        "Download TXT",
                        data=txt_path.read_text(encoding="utf-8"),
                        file_name=txt_path.name,
                        mime="text/plain",
                        key=f"hist_txt_{row['id']}"
                    )

                if md_path.exists():
                    st.download_button(
                        "Download MD",
                        data=md_path.read_text(encoding="utf-8"),
                        file_name=md_path.name,
                        mime="text/markdown",
                        key=f"hist_md_{row['id']}"
                    )


# ============================================================
# INPUT MODE
# ============================================================

input_mode = st.radio(
    "Sursă",
    ["YouTube link", "Upload fișier .txt/.vtt/.srt"],
    horizontal=True,
    label_visibility="collapsed"
)

source_url = None
uploaded_file = None
youtube_info = None
playlist_entries = []
selected_entries = []


if input_mode == "YouTube link":
    source_url = st.text_input(
        "Link YouTube",
        label_visibility="collapsed",
        placeholder="Paste YouTube link sau playlist..."
    )

    if source_url:
        with st.spinner("☕ Citesc metadata video/playlist..."):
            try:
                youtube_info = get_youtube_info(source_url)
                playlist_entries = flatten_playlist_entries(youtube_info)
            except Exception as e:
                st.error(f"Nu am putut citi linkul: {e}")
                youtube_info = None

        if youtube_info:
            is_playlist = len(playlist_entries) > 1

            if is_playlist:
                st.success(f"Playlist detectat: {len(playlist_entries)} video-uri")

                max_videos = st.slider(
                    "Câte video-uri să procesez din playlist?",
                    1,
                    min(len(playlist_entries), 50),
                    min(len(playlist_entries), 5)
                )

                selected_entries = playlist_entries[:max_videos]

                with st.expander("Video-uri selectate"):
                    for idx, entry in enumerate(selected_entries, start=1):
                        st.write(f"{idx}. {entry.get('title') or entry.get('id') or 'Untitled'}")
            else:
                selected_entries = [youtube_info]

                title = youtube_info.get("title") or "Untitled"
                channel = youtube_info.get("channel") or youtube_info.get("uploader") or "—"
                duration = format_duration(youtube_info.get("duration"))
                thumbnail = youtube_info.get("thumbnail")

                st.markdown('<div class="video-card">', unsafe_allow_html=True)

                if thumbnail:
                    st.image(thumbnail, use_container_width=True)

                st.markdown(f"### {title}")
                st.markdown(
                    f'<div class="small-muted">Canal: {channel} · Durată: {duration}</div>',
                    unsafe_allow_html=True
                )
                st.markdown("</div>", unsafe_allow_html=True)


if input_mode == "Upload fișier .txt/.vtt/.srt":
    uploaded_file = st.file_uploader(
        "Încarcă fișier transcript/subtitrare",
        type=["txt", "vtt", "srt"]
    )


# ============================================================
# OPTIONS
# ============================================================

st.markdown("## ⚙️ Opțiuni")

col_a, col_b = st.columns(2)

with col_a:
    keep_timestamps = st.checkbox("Păstrează timestamps", value=False)

with col_b:
    save_to_history_enabled = st.checkbox("Salvează în istoric", value=True)


selected_lang_label = None
selected_lang_code = None

if input_mode == "YouTube link" and youtube_info and selected_entries:
    first_url = get_entry_url(selected_entries[0])

    try:
        first_info = get_youtube_info(first_url)
        languages = collect_subtitle_languages(first_info)
    except Exception:
        languages = {}

    if languages:
        selected_lang_label = st.selectbox(
            "Subtitrare disponibilă",
            list(languages.keys()),
            index=0
        )
        selected_lang_code = languages[selected_lang_label]["lang"]
    else:
        st.warning("Nu am găsit subtitrări listabile pentru acest video. Poți încerca manual.")
        fallback_langs = {
            "EN": "en",
            "RO": "ro",
            "FR": "fr",
            "ES": "es",
            "DE": "de"
        }

        label = st.selectbox("Limbă manuală", list(fallback_langs.keys()))
        selected_lang_code = fallback_langs[label]


col1, col2, col3 = st.columns(3)

with col1:
    chunk_size = st.slider(
        "Caractere / chunk",
        min_value=2000,
        max_value=30000,
        value=15000,
        step=1000
    )

with col2:
    overlap_size = st.slider(
        "Overlap",
        min_value=0,
        max_value=3000,
        value=500,
        step=100
    )

with col3:
    chunk_mode = st.selectbox(
        "Tăiere",
        ["Pe propoziții", "Pe paragrafe", "Pe caractere"]
    )


st.markdown("## 🧠 Prompt AI")

prompt_mode = st.selectbox(
    "Preset",
    list(PROMPT_PRESETS.keys()),
    index=0
)

default_prompt = PROMPT_PRESETS[prompt_mode]

if prompt_mode == "Custom":
    default_prompt = """Rol:
Sarcină:
(Partea {part}/{total})

Transcript de procesat:
--------------------------------------------------
"""

with st.expander("Modifică promptul AI"):
    custom_prompt = st.text_area(
        "Prompt template",
        value=default_prompt,
        height=260,
        label_visibility="collapsed"
    )


# ============================================================
# PROCESS
# ============================================================

process_clicked = st.button("☕ Procesează", use_container_width=True)

if process_clicked:
    all_outputs = []

    if input_mode == "YouTube link":
        if not source_url or not selected_entries:
            st.error("Introdu un link YouTube valid.")
            st.stop()

        if not selected_lang_code:
            st.error("Alege o limbă de subtitrare.")
            st.stop()

        progress = st.progress(0)
        status = st.empty()

        for idx, entry in enumerate(selected_entries, start=1):
            entry_url = get_entry_url(entry)
            if not entry_url:
                continue

            status.info(f"Procesez video {idx}/{len(selected_entries)}...")

            try:
                full_info = get_youtube_info(entry_url)
                video_id = extract_video_id(full_info)
                title = full_info.get("title") or entry.get("title") or "Untitled"
                channel = full_info.get("channel") or full_info.get("uploader") or ""

                existing = find_existing_video(video_id, selected_lang_code)

                if existing:
                    st.info(
                        f"Video deja procesat anterior: {title} "
                        f"({existing['created_at']}). Îl procesez din nou cu setările actuale."
                    )

                transcript, info_after_download = extract_transcript_from_youtube(
                    entry_url,
                    selected_lang_code,
                    keep_timestamps
                )

                if not transcript or len(transcript) < 30:
                    st.warning(f"Nu am găsit transcript utilizabil pentru: {title}")
                    progress.progress(idx / len(selected_entries))
                    continue

                chunks = chunk_text(
                    transcript,
                    chunk_size=chunk_size,
                    overlap=overlap_size,
                    mode=chunk_mode
                )

                markdown_export = build_markdown_export(
                    title=title,
                    url=entry_url,
                    channel=channel,
                    language=selected_lang_code,
                    transcript=transcript,
                    chunks=chunks,
                    prompt_mode=prompt_mode,
                    prompt_template=custom_prompt
                )

                all_outputs.append({
                    "title": title,
                    "url": entry_url,
                    "video_id": video_id,
                    "channel": channel,
                    "language": selected_lang_code,
                    "transcript": transcript,
                    "chunks": chunks,
                    "markdown": markdown_export
                })

                if save_to_history_enabled:
                    save_history(
                        source_type="youtube",
                        url=entry_url,
                        video_id=video_id,
                        title=title,
                        channel=channel,
                        language=selected_lang_code,
                        transcript_text=transcript,
                        markdown_text=markdown_export,
                        char_count=len(transcript),
                        chunk_count=len(chunks),
                        prompt_mode=prompt_mode
                    )

            except Exception as e:
                st.error(f"Eroare la video {idx}: {e}")

            progress.progress(idx / len(selected_entries))

        status.success("Gata.")

    else:
        if not uploaded_file:
            st.error("Încarcă un fișier .txt, .vtt sau .srt.")
            st.stop()

        raw_content = uploaded_file.read()
        filename = uploaded_file.name
        suffix = Path(filename).suffix.lower()

        if suffix in [".vtt", ".srt"]:
            transcript = clean_subtitle_file(raw_content, keep_timestamps=keep_timestamps)
        else:
            transcript = raw_content.decode("utf-8", errors="ignore")
            transcript = clean_text_basic(transcript)

        if not transcript or len(transcript) < 30:
            st.error("Fișierul pare gol sau prea scurt.")
            st.stop()

        title = Path(filename).stem
        language = "local"

        chunks = chunk_text(
            transcript,
            chunk_size=chunk_size,
            overlap=overlap_size,
            mode=chunk_mode
        )

        markdown_export = build_markdown_export(
            title=title,
            url=None,
            channel=None,
            language=language,
            transcript=transcript,
            chunks=chunks,
            prompt_mode=prompt_mode,
            prompt_template=custom_prompt
        )

        all_outputs.append({
            "title": title,
            "url": None,
            "video_id": None,
            "channel": None,
            "language": language,
            "transcript": transcript,
            "chunks": chunks,
            "markdown": markdown_export
        })

        if save_to_history_enabled:
            save_history(
                source_type="upload",
                url=None,
                video_id=None,
                title=title,
                channel=None,
                language=language,
                transcript_text=transcript,
                markdown_text=markdown_export,
                char_count=len(transcript),
                chunk_count=len(chunks),
                prompt_mode=prompt_mode
            )

    if not all_outputs:
        st.error("Nu am obținut niciun transcript.")
        st.stop()

    st.markdown("## ✅ Rezultat")

    total_chars = sum(len(item["transcript"]) for item in all_outputs)
    total_tokens = estimate_tokens(" ".join(item["transcript"] for item in all_outputs))
    total_chunks = sum(len(item["chunks"]) for item in all_outputs)

    m1, m2, m3 = st.columns(3)

    with m1:
        st.metric("Caractere", f"{total_chars:,}")

    with m2:
        st.metric("Tokeni estimați", f"{total_tokens:,}")

    with m3:
        st.metric("Chunk-uri", total_chunks)

    files_for_zip = {}

    combined_txt_parts = []
    combined_md_parts = []

    for item in all_outputs:
        safe_title = sanitize_filename(item["title"])

        files_for_zip[f"{safe_title}.txt"] = item["transcript"]
        files_for_zip[f"{safe_title}.md"] = item["markdown"]

        combined_txt_parts.append(f"# {item['title']}\n\n{item['transcript']}\n\n")
        combined_md_parts.append(item["markdown"])

    combined_txt = "\n\n---\n\n".join(combined_txt_parts)
    combined_md = "\n\n---\n\n".join(combined_md_parts)

    files_for_zip["combined_transcripts.txt"] = combined_txt
    files_for_zip["combined_export.md"] = combined_md

    zip_mem = build_zip_file(files_for_zip)

    col_d1, col_d2, col_d3 = st.columns(3)

    with col_d1:
        st.download_button(
            "⬇️ TXT",
            data=combined_txt,
            file_name="dark_roast_transcript.txt",
            mime="text/plain",
            use_container_width=True
        )

    with col_d2:
        st.download_button(
            "⬇️ MD",
            data=combined_md,
            file_name="dark_roast_export.md",
            mime="text/markdown",
            use_container_width=True
        )

    with col_d3:
        st.download_button(
            "⬇️ ZIP",
            data=zip_mem,
            file_name="dark_roast_export.zip",
            mime="application/zip",
            use_container_width=True
        )

    for item_index, item in enumerate(all_outputs, start=1):
        st.markdown("---")
        st.markdown(f"## {item['title']}")

        if item["url"]:
            st.caption(item["url"])

        with st.expander("Transcript curat", expanded=False):
            st.code(item["transcript"], language="text")

        st.markdown("### AI chunks")

        chunk_tabs = st.tabs([f"Partea {i+1}" for i in range(len(item["chunks"]))])

        total = len(item["chunks"])

        for i, tab in enumerate(chunk_tabs):
            with tab:
                chunk_text_part = item["chunks"][i]

                try:
                    header = custom_prompt.format(part=i + 1, total=total)
                except Exception:
                    header = custom_prompt + f"\n\n(Partea {i + 1}/{total})\n--------------------------------------------------\n"

                final_prompt = header + chunk_text_part

                st.caption(
                    f"Partea {i + 1}/{total} · "
                    f"{len(chunk_text_part):,} caractere · "
                    f"~{estimate_tokens(chunk_text_part):,} tokeni"
                )

                st.code(final_prompt, language="text")

        with st.expander("Markdown export complet"):
            st.code(item["markdown"], language="markdown")
