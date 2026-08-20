# Paper Counter

A very simple paper counting web app built with **Python + Flask** and a **Turso (libSQL)** database.

It has two cards — **Used Paper** and **Unused Paper** — each with a large number and **+ / -** buttons.
A Settings page shows the **Student Name**, **Machine Name**, and the **Total Paper**
(`total = used + unused`). A Stats page shows a pie chart breakdown. Every change is saved to the
database immediately.

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

## 3. Add the environment variables

The app reads two environment variables: `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN`.

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```
TURSO_DATABASE_URL=libsql://paper-counter-yourname.turso.io
TURSO_AUTH_TOKEN=your-long-auth-token-here
```

> Do not commit `.env` to GitHub. Keep your token private.

## 4. Run locally

```bash
# 1. (optional) create a virtual environment
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

# 2. install the requirements
pip install -r requirements.txt

# 3. run the app
python app.py
```

Then open http://localhost:8501 in your browser.

## 5. Deploy

Deploy anywhere that runs a Python/Flask app (Render, Railway, Fly.io, a VPS, etc.).
Set `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` as environment variables on the host,
and run the app with a production WSGI server, e.g.:

```bash
pip install gunicorn
gunicorn app:app --bind 0.0.0.0:8501
```

---

## Project structure

```
paper_counter_app/
│
├── app.py                 # Flask app: routes + database logic
├── templates/
│   ├── base.html           # shared layout, rainbow title, bottom nav
│   ├── home.html            # Used / Unused paper cards
│   ├── stats.html           # pie chart breakdown
│   ├── settings.html        # student/machine name form
│   └── error.html           # shown when DB credentials/connection fail
├── static/
│   └── style.css            # all app styling
├── requirements.txt        # Python packages
├── .env.example             # template for TURSO_* environment variables
└── README.md                # this file
```

## How it works (for the presentation)

- On startup the app connects to Turso (lazily, on first request) and runs `init_db()`,
  which creates the `paper_counter` table if needed and adds one default row.
- Every route calls `load_data()` to read that row fresh from the database — there is no
  client-side session cache, so the numbers shown are always up to date.
- Clicking **+** or **-** on the Home page submits a small form to `/update/<kind>/<action>`,
  which updates the count, calls `save_data()` to write it to the database, and redirects
  back to Home. The count never goes below 0.
- The Settings page auto-submits when a text field loses focus (and also has a Save button),
  updating the student/machine name in the database.
- The Stats page renders a Chart.js pie chart of used vs. unused paper.
