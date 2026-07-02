# ☕ Dark Roast Scholar

Lipești un link YouTube → aplicația extrage subtitrarea disponibilă, o curăță și o împarte în prompturi AI-ready pe care le copiezi manual în ChatGPT / Claude / Gemini pentru un **rezumat scurt și util** al videoclipului.

Fără API keys, fără login, fără baze de date externe.

## Cum funcționează

1. Introduci linkul și apeși **„Extrage transcriptul"**.
2. Aplicația detectează subtitrările prin `yt-dlp` și alege automat cea mai bună:
   - subtitrare **manuală** în limba originală a videoclipului
   - apoi manuală într-o limbă majoră (en, fr, ro, es, de, it)
   - apoi orice subtitrare manuală
   - apoi subtitrare **automată** în limba vorbită
   - apoi automată într-o limbă majoră
   - dacă există mai multe variante, poți schimba limba dintr-un selectbox
3. Textul este curățat (timestampuri, taguri HTML, duplicate consecutive, spații).
4. Transcriptul este împărțit în fragmente de ~12.000 caractere, cu suprapunere de ~400 caractere, tăiat pe propoziții.
5. Fiecare fragment primește un prompt de rezumat, într-un bloc cu buton de copiere.
6. Poți descărca: transcriptul `.txt`, prompturile `.md` sau totul într-un `.zip`.

## Rulare locală

```bash
git clone <repo-ul-tau>
cd dark-roast-scholar

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

Aplicația se deschide la `http://localhost:8501`.

## Deploy pe Render

### Varianta 1 — Blueprint (recomandat)

1. Urcă proiectul într-un repo GitHub (include `render.yaml`).
2. În Render: **New → Blueprint** → selectează repo-ul.
3. Render citește `render.yaml` și configurează totul automat. Deploy.

### Varianta 2 — manual (Web Service)

1. **New → Web Service** → conectează repo-ul.
2. Runtime: **Python**.
3. Build command:
   ```
   pip install -r requirements.txt
   ```
4. Start command:
   ```
   streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
   ```
5. Deploy.

## Configurare (variabile de mediu)

| Variabilă | Efect |
|---|---|
| `DRS_DISABLE_HISTORY=1` | Dezactivează complet istoricul local SQLite (recomandat pe Render). |
| `DRS_DATA_DIR=/cale/dir` | Schimbă directorul unde se salvează baza de date de istoric. |

Istoricul este **best-effort**: dacă SQLite nu poate scrie pe disc, aplicația continuă normal, fără erori.

## Limitări cunoscute

- **YouTube poate bloca IP-urile de datacenter** (inclusiv Render) cu mesaje de tip „Sign in to confirm you're not a bot". Aplicația afișează un mesaj prietenos în acest caz. Local funcționează normal; pe Render poate fi intermitent — asta e o limitare YouTube, nu a aplicației.
- Pe planul free Render, discul este efemer: istoricul (dacă e activat) se pierde la redeploy.
- Videoclipurile fără nicio subtitrare (nici automată) nu pot fi procesate — aplicația nu face speech-to-text.

## Structura proiectului

```
dark-roast-scholar/
├── app.py            # toată aplicația (UI + logică)
├── requirements.txt
├── render.yaml       # blueprint Render
├── README.md
└── .gitignore
```
