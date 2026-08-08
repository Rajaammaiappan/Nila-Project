# Paper Counter

A very simple paper counting web app built with **Python + Streamlit** and a **Turso (libSQL)** database.

It has two cards — **Used Paper** and **Unused Paper** — each with a large number and **+ / -** buttons.
A narrow panel on the right shows the **Student Name**, **Machine Name**, and the **Total Paper**
(`total = used + unused`). Every change is saved to the database immediately.

---

## 1. Create a Turso database

1. Install the Turso CLI: https://docs.turso.tech/cli/installation
2. Sign up / log in:
   ```bash
   turso auth signup
   ```
3. Create a database:
   ```bash
   turso db create paper-counter
   ```

## 2. Get the database URL and auth token

1. Get the database URL:
   ```bash
   turso db show paper-counter --url
   ```
   It looks like: `libsql://paper-counter-yourname.turso.io`

2. Create an auth token:
   ```bash
   turso db tokens create paper-counter
   ```
   Copy the long token string it prints.

## 3. Add the Streamlit secrets

The app reads two secrets: `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN`.

**For running locally**, create a file at `.streamlit/secrets.toml`:

```toml
TURSO_DATABASE_URL = "libsql://paper-counter-yourname.turso.io"
TURSO_AUTH_TOKEN = "your-long-auth-token-here"
```

> Do not commit `secrets.toml` to GitHub. Keep your token private.

## 4. Run locally

```bash
# 1. (optional) create a virtual environment
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

# 2. install the requirements
pip install -r requirements.txt

# 3. run the app
streamlit run app.py
```

Then open the link shown in the terminal (usually http://localhost:8501).

## 5. Deploy on Streamlit Cloud

1. Push this project to a **GitHub** repository.
2. Go to https://share.streamlit.io and click **New app**.
3. Choose your repository, branch, and set the main file to `app.py`.
4. Open **Advanced settings → Secrets** and paste:
   ```toml
   TURSO_DATABASE_URL = "libsql://paper-counter-yourname.turso.io"
   TURSO_AUTH_TOKEN = "your-long-auth-token-here"
   ```
5. Click **Deploy**. Your app will be live on a public URL.

---

## Project structure

```
paper_counter_app/
│
├── app.py                 # the whole application
├── requirements.txt       # Python packages
├── .streamlit/
│   └── config.toml        # Streamlit settings
└── README.md              # this file
```

## How it works (for the presentation)

- On startup the app connects to Turso and runs `init_db()`, which creates the
  `paper_counter` table if needed and adds one default row.
- `load_data()` reads that row once and keeps the numbers in `st.session_state`.
- Clicking **+** or **-** changes the number, calls `save_data()` to write it to
  the database, and refreshes the screen. The count never goes below 0.
- The right panel adds the two numbers together to show the **Total Paper**.
