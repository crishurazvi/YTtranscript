"""
Dark Roast Scholar — YouTube transcript → AI-ready summary prompts.

Flow: paste a YouTube link → the app picks the best available subtitle
(manual preferred, original language preferred), cleans it, splits it into
chunks and wraps each chunk in a summary-oriented prompt ready to paste
into ChatGPT / Claude / Gemini.

No API keys, no login, no external databases. Optional local SQLite history.
"""

import html
import io
import json
import os
import re
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
import yt_dlp


# ============================================================
# CONFIG
# ============================================================

APP_TITLE = "☕ Dark Roast Scholar"
APP_SUBTITLE = "Lipește un link YouTube → primești prompturi gata de copiat în AI, pentru un rezumat scurt și util."

MAJOR_LANGS = ["en", "fr", "ro", "es", "de", "it"]

DEFAULT_CHUNK_SIZE = 12000
DEFAULT_OVERLAP = 400

# History can be disabled entirely (useful on Render, where the disk is
# ephemeral and history is lost on every redeploy anyway).
HISTORY_ENABLED = os.environ.get("DRS_DISABLE_HISTORY", "0") != "1"

DATA_DIR = Path(os.environ.get("DRS_DATA_DIR", "dark_roast_data"))
DB_PATH = DATA_DIR / "history.sqlite"

DEFAULT_PROMPT = """Rol: Ești un asistent expert în extragerea ideilor importante din transcripturi video.

Sarcină: Analizează următorul fragment de transcript și extrage doar informațiile importante.

Vreau un rezumat scurt, clar și util, în limba română.

Nu traduce fidel fiecare frază.
Nu face articol lung.
Nu inventa informații care nu apar în transcript.
Elimină repetițiile, exemplele inutile și umplutura verbală.
Păstrează doar ideile, explicațiile, concluziile și detaliile cu valoare reală.

Format de ieșire dorit:

- Rezumat scurt al fragmentului
- Idei-cheie
- Concepte importante
- Ce merită reținut
- Eventuale întrebări sau puncte neclare, dacă există

Acesta este fragmentul {part}/{total}:

"""


# ============================================================
# PAGE + THEME
# ============================================================

st.set_page_config(
    page_title="Dark Roast Scholar",
    page_icon="☕",
    layout="centered",
)

st.markdown("""
<style>
    #MainMenu, footer, header {visibility: hidden;}

    .stApp {
        background: radial-gradient(ellipse at top, #16110C 0%, #0C0A08 55%) fixed;
        color: #E8E2D9;
    }

    .block-container {max-width: 780px; padding-top: 2.5rem;}

    h1, h2, h3, h4 {
        color: #D4A373 !important;
        font-weight: 400 !important;
        letter-spacing: 0.01em;
    }

    .drs-eyebrow {
        color: #8A7A64;
        font-size: 0.78rem;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        text-align: center;
        margin-bottom: 0.2rem;
    }

    .drs-title {
        text-align: center;
        font-size: 2.3rem;
        color: #D4A373;
        margin: 0;
    }

    .drs-sub {
        text-align: center;
        color: #A89C8B;
        font-size: 0.98rem;
        max-width: 560px;
        margin: 0.5rem auto 0.2rem auto;
        line-height: 1.5;
    }

    .drs-rule {
        height: 1px;
        width: 120px;
        margin: 1.1rem auto 1.6rem auto;
        background: linear-gradient(90deg, transparent, #BC6C25, transparent);
    }

    .stTextInput > div > div > input {
        background-color: #14100C;
        color: #F3EDE3;
        border: 1px solid #3A3227;
        border-radius: 10px;
        padding: 14px 16px;
        font-size: 16px;
    }
    .stTextInput > div > div > input:focus {
        border-color: #D4A373;
        box-shadow: 0 0 0 1px #D4A37344;
    }

    .stTextArea > div > div > textarea {
        background-color: #14100C;
        color: #F3EDE3;
        border: 1px solid #3A3227;
        border-radius: 10px;
    }
    .stTextArea > div > div > textarea:focus {
        border-color: #D4A373;
        box-shadow: none;
    }

    .stSelectbox > div > div {
        background-color: #14100C;
        color: #F3EDE3;
        border: 1px solid #3A3227;
        border-radius: 10px;
    }

    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
        background: linear-gradient(180deg, #C87B33, #A65E1F);
        color: #17110A;
        border: none;
        border-radius: 10px;
        padding: 0.65rem 1.4rem;
        font-weight: 600;
        width: 100%;
    }
    .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
        background: linear-gradient(180deg, #D68A3E, #B4682A);
        color: #17110A;
    }

    .stCode, div[data-testid="stCode"] pre {
        background-color: #100D0A !important;
        border: 1px solid #2E2820 !important;
        border-left: 3px solid #BC6C25 !important;
        border-radius: 10px;
    }

    div[data-testid="stMetric"] {
        background-color: #120E0B;
        border: 1px solid #2C251D;
        padding: 12px;
        border-radius: 12px;
    }
    div[data-testid="stMetric"] label {color: #A89C8B !important;}
    div[data-testid="stMetricValue"] {color: #D4A373 !important;}

    .drs-card {
        background-color: #110D0A;
        border: 1px solid #2C251D;
        border-radius: 14px;
        padding: 16px 18px;
        margin: 10px 0 4px 0;
    }
    .drs-card .t {color: #D4A373; font-size: 1.05rem;}
    .drs-card .m {color: #A89C8B; font-size: 0.88rem; margin-top: 2px;}

    .streamlit-expanderHeader, details summary {
        color: #C8B89E !important;
    }

    .stAlert {border-radius: 10px;}
</style>
""", unsafe_allow_html=True)


# ============================================================
# LOCAL HISTORY (optional, best-effort — never crashes the app)
# ============================================================

def _db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if not HISTORY_ENABLED:
        return
    try:
        with _db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    url TEXT,
                    video_id TEXT,
                    title TEXT,
                    language TEXT,
                    char_count INTEGER,
                    chunk_count INTEGER
                )
            """)
    except Exception:
        pass


def save_history(url, video_id, title, language, char_count, chunk_count):
    if not HISTORY_ENABLED:
        return
    try:
        with _db() as conn:
            conn.execute(
                """INSERT INTO history
                   (created_at, url, video_id, title, language, char_count, chunk_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    url, video_id, title, language, char_count, chunk_count,
                ),
            )
    except Exception:
        pass


def get_history(limit=15):
    if not HISTORY_ENABLED:
        return []
    try:
        with _db() as conn:
            rows = conn.execute(
                "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return rows
    except Exception:
        return []


init_db()


# ============================================================
# TEXT UTILS
# ============================================================

def sanitize_filename(name):
    if not name:
        return "transcript"
    name = re.sub(r"[^\w\s.-]", "", name, flags=re.UNICODE)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:80] or "transcript"


def estimate_tokens(text):
    return max(1, int(len(text) / 4))


def copy_button(text, label):
    """One-click copy-to-clipboard button (no prompt preview)."""
    payload = json.dumps(text).replace("</", "<\\/")
    components.html(f"""
        <style>
            body {{ margin: 0; }}
            .copy-btn {{
                width: 100%; padding: 11px 0;
                background: linear-gradient(180deg, #C87B33, #A65E1F);
                color: #17110A; border: none; border-radius: 10px;
                font-weight: 600; font-size: 14px;
                font-family: "Source Sans Pro", sans-serif; cursor: pointer;
            }}
            .copy-btn:hover {{ background: linear-gradient(180deg, #D68A3E, #B4682A); }}
            .copy-btn.done {{ background: #2E4B2E; color: #C9E3C9; }}
        </style>
        <button class="copy-btn" onclick="copyText(this)">{label}</button>
        <script>
            const TEXT = {payload};
            function fallbackCopy() {{
                const ta = document.createElement("textarea");
                ta.value = TEXT;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand("copy");
                document.body.removeChild(ta);
            }}
            function copyText(btn) {{
                if (navigator.clipboard && navigator.clipboard.writeText) {{
                    navigator.clipboard.writeText(TEXT).catch(fallbackCopy);
                }} else {{ fallbackCopy(); }}
                btn.innerText = "\\u2714 Copiat";
                btn.classList.add("done");
                setTimeout(() => {{
                    btn.innerText = "{label}";
                    btn.classList.remove("done");
                }}, 1600);
            }}
        </script>
    """, height=48)


def clean_text_basic(text):
    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_subtitle_file(content):
    """Clean a VTT/SRT file: drop timestamps, HTML tags, cue numbers and
    consecutive duplicate lines produced by auto-captions."""
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="ignore")

    content = html.unescape(content)
    output = []
    previous = ""

    for raw in content.splitlines():
        line = raw.strip()
        if not line:
            continue

        upper = line.upper()
        if upper.startswith(("WEBVTT", "NOTE", "KIND:", "LANGUAGE:", "STYLE")):
            continue
        if re.fullmatch(r"\d+", line):          # SRT cue numbers
            continue
        if "-->" in line:                        # timestamp lines
            continue

        line = re.sub(r"<[^>]+>", "", line)      # HTML/word-timing tags
        line = clean_text_basic(line)
        if not line:
            continue

        # auto-captions repeat the same rolling line — keep one copy
        if line == previous:
            continue
        previous = line
        output.append(line)

    text = " ".join(output)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    return text.strip()


def split_sentences(text):
    text = clean_text_basic(text)

    protected = {
        "Dr.": "Dr§", "Prof.": "Prof§", "Mr.": "Mr§", "Mrs.": "Mrs§",
        "e.g.": "eg§", "i.e.": "ie§", "etc.": "etc§", "vs.": "vs§",
    }
    for k, v in protected.items():
        text = text.replace(k, v)

    parts = re.split(r"(?<=[.!?])\s+", text)

    restored = []
    for part in parts:
        for k, v in protected.items():
            part = part.replace(v, k)
        part = part.strip()
        if part:
            restored.append(part)
    return restored


def chunk_text(text, chunk_size=DEFAULT_CHUNK_SIZE, overlap=DEFAULT_OVERLAP):
    """Sentence-aware chunking with a small overlap between chunks."""
    text = clean_text_basic(text)
    if len(text) <= chunk_size:
        return [text]

    sentences = split_sentences(text)
    chunks = []
    current = ""

    for sentence in sentences:
        # a single sentence longer than the chunk size gets hard-split
        while len(sentence) > chunk_size:
            head, sentence = sentence[:chunk_size], sentence[chunk_size:]
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.append(head.strip())

        if not current:
            current = sentence
        elif len(current) + len(sentence) + 1 <= chunk_size:
            current += " " + sentence
        else:
            chunks.append(current.strip())
            tail = current[-overlap:].strip() if overlap > 0 else ""
            current = (tail + " " + sentence).strip()

    if current.strip():
        chunks.append(current.strip())
    return chunks


def build_prompts(chunks, template):
    total = len(chunks)
    prompts = []
    for idx, chunk in enumerate(chunks, start=1):
        try:
            header = template.format(part=idx, total=total)
        except (KeyError, IndexError, ValueError):
            header = template + f"\n(Fragmentul {idx}/{total})\n\n"
        prompts.append(header + chunk)
    return prompts


def build_markdown_export(title, url, language, transcript, prompts):
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    md = [
        "---",
        f'title: "{(title or "Untitled").replace(chr(34), "")}"',
        f'source: "{url or ""}"',
        f'language: "{language or ""}"',
        f'date: "{date_str}"',
        "tags: [youtube, transcript, dark-roast-scholar]",
        "---",
        "",
        f"# {title or 'Transcript'}",
        "",
        f"Sursă: {url}" if url else "",
        "",
        "## Transcript curat",
        "",
        transcript,
        "",
        "---",
        "",
        "## Prompturi AI (copiază fiecare bloc separat)",
        "",
    ]
    for idx, prompt in enumerate(prompts, start=1):
        md.append(f"### Fragmentul {idx}/{len(prompts)}")
        md.append("")
        md.append("```text")
        md.append(prompt)
        md.append("```")
        md.append("")
    return "\n".join(md)


def build_prompts_txt(prompts):
    sep = "\n\n" + "=" * 60 + "\n\n"
    blocks = [
        f"### FRAGMENTUL {i}/{len(prompts)} ###\n\n{p}"
        for i, p in enumerate(prompts, start=1)
    ]
    return sep.join(blocks)


def build_zip(files_dict):
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files_dict.items():
            zf.writestr(filename, content)
    mem.seek(0)
    return mem.getvalue()


# ============================================================
# YOUTUBE
# ============================================================

YOUTUBE_URL_RE = re.compile(
    r"(https?://)?(www\.|m\.|music\.)?"
    r"(youtube\.com/(watch\?|shorts/|live/|embed/)|youtu\.be/)",
    re.IGNORECASE,
)


def looks_like_youtube_url(url):
    return bool(YOUTUBE_URL_RE.search(url.strip()))


def friendly_ytdlp_error(err):
    msg = str(err).lower()
    if "private" in msg:
        return "Videoclipul este privat — nu îi pot accesa subtitrările."
    if "unavailable" in msg or "removed" in msg:
        return "Videoclipul nu este disponibil (șters, blocat sau restricționat regional)."
    if "age" in msg and "confirm" in msg:
        return "Videoclipul are restricție de vârstă și nu poate fi accesat fără autentificare."
    if "sign in" in msg or "bot" in msg or "captcha" in msg:
        return ("YouTube a blocat temporar cererea (protecție anti-bot). "
                "Încearcă din nou peste câteva minute sau rulează aplicația local.")
    if "unsupported url" in msg or "invalid" in msg:
        return "Linkul nu pare să fie un videoclip YouTube valid."
    if "network" in msg or "timed out" in msg or "connection" in msg:
        return "Conexiunea la YouTube a eșuat. Verifică internetul și reîncearcă."
    return "Nu am putut procesa acest link. Verifică-l și încearcă din nou."


@st.cache_data(show_spinner=False, ttl=3600)
def get_video_info(url):
    opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if info and info.get("_type") == "playlist":
        entries = [e for e in (info.get("entries") or []) if e]
        if not entries:
            return None
        info = entries[0]

    # keep only what the UI needs (also keeps the cache small)
    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "channel": info.get("channel") or info.get("uploader"),
        "duration": info.get("duration"),
        "language": (info.get("language") or "").split("-")[0].lower(),
        "webpage_url": info.get("webpage_url") or url,
        "manual_langs": sorted((info.get("subtitles") or {}).keys()),
        "auto_langs": sorted((info.get("automatic_captions") or {}).keys()),
    }


def build_subtitle_options(info):
    """Return (options, best_key). options: {label: {"lang", "type"}}.

    Preference order:
      1. manual subtitle in the video's original language
      2. manual subtitle in a major language (en, fr, ro, es, de, it)
      3. any manual subtitle
      4. auto captions in the original spoken language
      5. auto captions in a major language
    """
    original = info.get("language") or ""
    manual = info.get("manual_langs") or []
    auto = info.get("auto_langs") or []

    def base(code):
        return code.split("-")[0].lower()

    options = {}

    def add(lang, kind):
        label = f"{lang} · {'manuală' if kind == 'manual' else 'automată'}"
        if label not in options:
            options[label] = {"lang": lang, "type": kind}
        return label

    ranked = []

    # 1–3: manual subtitles
    for lang in manual:
        if original and base(lang) == original:
            ranked.append((0, add(lang, "manual")))
        elif base(lang) in MAJOR_LANGS:
            ranked.append((1, add(lang, "manual")))
        else:
            ranked.append((2, add(lang, "manual")))

    # 4: auto captions in the spoken language ("xx-orig" or matching original)
    for lang in auto:
        if lang.endswith("-orig") or (original and base(lang) == original):
            ranked.append((3, add(lang, "auto")))

    # 5: auto captions in major languages (skip the flood of machine
    #    translations — only major langs are offered)
    for lang in auto:
        if lang.endswith("-orig"):
            continue
        if base(lang) in MAJOR_LANGS:
            ranked.append((4, add(lang, "auto")))

    # last resort: any auto caption at all
    if not ranked and auto:
        ranked.append((5, add(auto[0], "auto")))

    if not ranked:
        return {}, None

    ranked.sort(key=lambda t: t[0])
    return options, ranked[0][1]


@st.cache_data(show_spinner=False, ttl=3600)
def download_subtitle(url, lang_code, sub_type):
    """Download one subtitle track via yt-dlp and return cleaned text."""
    with tempfile.TemporaryDirectory() as tmpdir:
        options = {
            "skip_download": True,
            "writesubtitles": sub_type == "manual",
            "writeautomaticsub": sub_type == "auto",
            "subtitleslangs": [lang_code],
            "subtitlesformat": "vtt/srt/best",
            "outtmpl": os.path.join(tmpdir, "subtitle.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.extract_info(url, download=True)

        files = []
        for ext in ("vtt", "srt"):
            files.extend(Path(tmpdir).glob(f"*.{ext}"))
        if not files:
            return None

        content = files[0].read_text(encoding="utf-8", errors="ignore")
        return clean_subtitle_file(content)


def format_duration(seconds):
    if not seconds:
        return "—"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m}m" if h else f"{m}m {s}s"


# ============================================================
# SIDEBAR — history
# ============================================================

with st.sidebar:
    st.markdown("### 📚 Istoric local")
    if not HISTORY_ENABLED:
        st.caption("Istoricul este dezactivat (DRS_DISABLE_HISTORY=1).")
    else:
        rows = get_history()
        if not rows:
            st.caption("Încă nu ai extras niciun transcript.")
        for row in rows:
            st.markdown(
                f"**{(row['title'] or 'Untitled')[:42]}**  \n"
                f"<span style='color:#8A7A64;font-size:0.8rem'>"
                f"{row['created_at']} · {row['language']} · "
                f"{row['chunk_count']} fragmente</span>",
                unsafe_allow_html=True,
            )
            if row["url"]:
                st.caption(row["url"])
            st.divider()


# ============================================================
# MAIN UI
# ============================================================

st.markdown('<div class="drs-eyebrow">transcript · curățare · prompturi</div>', unsafe_allow_html=True)
st.markdown(f'<h1 class="drs-title">{APP_TITLE}</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="drs-sub">{APP_SUBTITLE}</p>', unsafe_allow_html=True)
st.markdown('<div class="drs-rule"></div>', unsafe_allow_html=True)

with st.form("url_form", clear_on_submit=False):
    url = st.text_input(
        "Link YouTube",
        placeholder="https://www.youtube.com/watch?v=...",
        label_visibility="collapsed",
    )
    submitted = st.form_submit_button("☕ Extrage transcriptul")

with st.expander("⚙️ Setări avansate (opțional)"):
    chunk_size = st.slider("Dimensiune fragment (caractere)", 6000, 20000, DEFAULT_CHUNK_SIZE, 1000)
    overlap = st.slider("Suprapunere între fragmente (caractere)", 0, 800, DEFAULT_OVERLAP, 50)
    prompt_template = st.text_area(
        "Prompt (folosește {part} și {total})",
        value=DEFAULT_PROMPT,
        height=260,
    )

if submitted:
    st.session_state.pop("result", None)

    if not url.strip():
        st.warning("Lipește mai întâi un link YouTube.")
    elif not looks_like_youtube_url(url):
        st.error("Acesta nu pare a fi un link YouTube valid. Exemplu: https://www.youtube.com/watch?v=...")
    else:
        try:
            with st.spinner("Citesc informațiile videoclipului..."):
                info = get_video_info(url.strip())
        except yt_dlp.utils.DownloadError as e:
            info = None
            st.error(friendly_ytdlp_error(e))
        except Exception:
            info = None
            st.error("A apărut o eroare neașteptată la citirea videoclipului. Încearcă din nou.")

        if info:
            options, best = build_subtitle_options(info)
            if not options:
                st.error("Acest videoclip nu are nicio subtitrare disponibilă (nici manuală, nici automată).")
            else:
                st.session_state["video"] = {"info": info, "options": options, "best": best, "url": url.strip()}
                st.session_state.pop("chosen_label", None)

# ---- video found: language choice + extraction ----
video_state = st.session_state.get("video")

if video_state:
    info = video_state["info"]
    options = video_state["options"]
    best = video_state["best"]
    source_url = video_state["url"]

    st.markdown(
        f"""<div class="drs-card">
              <div class="t">{html.escape(info.get("title") or "Untitled")}</div>
              <div class="m">{html.escape(info.get("channel") or "")} · {format_duration(info.get("duration"))}
              · {len(options)} subtitrări disponibile</div>
            </div>""",
        unsafe_allow_html=True,
    )

    labels = list(options.keys())
    if len(labels) > 1:
        chosen_label = st.selectbox(
            "Limba subtitrării",
            labels,
            index=labels.index(best) if best in labels else 0,
        )
    else:
        chosen_label = labels[0]
        st.caption(f"Subtitrare folosită: **{chosen_label}**")

    chosen = options[chosen_label]

    # (re)extract when needed: new video, or the user changed the language
    result = st.session_state.get("result")
    need_extract = (
        result is None
        or result.get("url") != source_url
        or result.get("label") != chosen_label
    )

    if need_extract:
        try:
            with st.spinner("Descarc și curăț subtitrarea..."):
                transcript = download_subtitle(source_url, chosen["lang"], chosen["type"])
        except yt_dlp.utils.DownloadError as e:
            transcript = None
            st.error(friendly_ytdlp_error(e))
        except Exception:
            transcript = None
            st.error("Subtitrarea nu a putut fi descărcată. Încearcă altă limbă sau alt videoclip.")

        if transcript is not None and not transcript.strip():
            transcript = None
            st.error("Subtitrarea a fost găsită, dar este goală după curățare. Încearcă altă limbă.")

        if transcript:
            st.session_state["result"] = {
                "url": source_url,
                "label": chosen_label,
                "lang": chosen["lang"],
                "transcript": transcript,
            }
            save_history(
                source_url, info.get("id"), info.get("title"),
                chosen["lang"], len(transcript),
                len(chunk_text(transcript, chunk_size, overlap)),
            )
        result = st.session_state.get("result")

    # ---- results ----
    if result and result.get("label") == chosen_label:
        transcript = result["transcript"]
        chunks = chunk_text(transcript, chunk_size, overlap)
        prompts = build_prompts(chunks, prompt_template)

        c1, c2, c3 = st.columns(3)
        c1.metric("Caractere", f"{len(transcript):,}")
        c2.metric("Tokens (estimat)", f"{estimate_tokens(transcript):,}")
        c3.metric("Fragmente", len(chunks))

        with st.expander("📄 Transcriptul curat (previzualizare)"):
            st.text_area(
                "Transcript",
                value=transcript,
                height=240,
                label_visibility="collapsed",
            )

        st.markdown("## ✂️ Copiază prompturile")
        st.caption(
            "Apasă un buton ca să copiezi promptul complet în clipboard, "
            "apoi lipește-l în ChatGPT, Claude sau Gemini. "
            "Fiecare prompt este independent."
        )

        items = list(enumerate(prompts, start=1))
        for start in range(0, len(items), 3):
            cols = st.columns(3)
            for col, (idx, prompt) in zip(cols, items[start:start + 3]):
                with col:
                    copy_button(prompt, f"📋 Fragment {idx}/{len(items)}")

        # ---- export ----
        st.markdown("## ⬇️ Export")

        base_name = sanitize_filename(info.get("title") or info.get("id"))
        md_export = build_markdown_export(
            info.get("title"), source_url, chosen_label, transcript, prompts
        )
        prompts_txt = build_prompts_txt(prompts)

        e1, e2, e3 = st.columns(3)
        with e1:
            st.download_button(
                "Transcript .txt",
                data=transcript,
                file_name=f"{base_name}.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with e2:
            st.download_button(
                "Prompturi .md",
                data=md_export,
                file_name=f"{base_name}_prompts.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with e3:
            st.download_button(
                "Tot (.zip)",
                data=build_zip({
                    f"{base_name}.txt": transcript,
                    f"{base_name}_prompts.txt": prompts_txt,
                    f"{base_name}_prompts.md": md_export,
                }),
                file_name=f"{base_name}.zip",
                mime="application/zip",
                use_container_width=True,
            )

st.markdown(
    '<p style="text-align:center;color:#5C5245;font-size:0.8rem;margin-top:3rem">'
    "Dark Roast Scholar · fără API keys · fără login · datele rămân la tine</p>",
    unsafe_allow_html=True,
)
