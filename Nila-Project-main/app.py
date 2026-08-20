import os
from datetime import datetime

import libsql_client
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request

load_dotenv()

app = Flask(__name__)

_client = None


# ------------------------------------------------------------------
# Read the database credentials from environment variables (.env)
# ------------------------------------------------------------------
def get_credentials():
    """Return (url, token) from the environment, or (None, None) if missing."""
    url = os.environ.get("TURSO_DATABASE_URL")
    token = os.environ.get("TURSO_AUTH_TOKEN")
    return url, token


# ------------------------------------------------------------------
# Create ONE database client and reuse it
# ------------------------------------------------------------------
def get_client():
    """Create (once) and return a Turso client."""
    global _client
    if _client is not None:
        return _client

    url, token = get_credentials()
    if not url or not token:
        return None

    # The sync client turns libsql:// into a websocket (wss://) that Turso
    # rejects. Switching to https:// makes it use HTTP, which works.
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "https://", 1)

    _client = libsql_client.create_client_sync(url=url, auth_token=token)
    return _client


# ------------------------------------------------------------------
# Database functions
# ------------------------------------------------------------------
def init_db(client):
    """Create the table if it does not exist and add a default row if empty."""
    client.execute(
        """
        CREATE TABLE IF NOT EXISTS paper_counter (
            id INTEGER PRIMARY KEY,
            student_name TEXT,
            machine_name TEXT,
            used_paper INTEGER,
            unused_paper INTEGER,
            updated_at TEXT
        )
        """
    )

    result = client.execute("SELECT COUNT(*) FROM paper_counter")
    count = result.rows[0][0]

    if count == 0:
        client.execute(
            """
            INSERT INTO paper_counter
                (id, student_name, machine_name, used_paper, unused_paper, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [1, "School Student", "Machine 1", 0, 0, datetime.now().isoformat()],
        )


def load_data(client):
    """Read the single record (id = 1) and return it as a dictionary."""
    result = client.execute(
        "SELECT student_name, machine_name, used_paper, unused_paper "
        "FROM paper_counter WHERE id = 1"
    )
    row = result.rows[0]
    return {
        "student_name": row[0],
        "machine_name": row[1],
        "used_paper": row[2],
        "unused_paper": row[3],
    }


def save_data(client, student_name, machine_name, used_paper, unused_paper):
    """Save the current values back into the database."""
    client.execute(
        """
        UPDATE paper_counter
        SET student_name = ?,
            machine_name = ?,
            used_paper = ?,
            unused_paper = ?,
            updated_at = ?
        WHERE id = 1
        """,
        [student_name, machine_name, used_paper, unused_paper, datetime.now().isoformat()],
    )


# ------------------------------------------------------------------
# Paper icons (drawn with inline SVG, one per count)
# ------------------------------------------------------------------
def paper_icon(color, lined):
    """Return an SVG paper sheet. lined=True adds writing lines (used paper)."""
    lines = ""
    if lined:
        lines = (
            '<line x1="8" y1="9" x2="11" y2="9"/>'
            '<line x1="8" y1="13" x2="16" y2="13"/>'
            '<line x1="8" y1="17" x2="16" y2="17"/>'
        )
    return (
        f'<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.7" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
        '<path d="M14 2v6h6"/>'
        f"{lines}</svg>"
    )


USED_ICON = paper_icon("#E91E8C", lined=True)     # pink written sheet
UNUSED_ICON = paper_icon("#43A047", lined=False)  # green blank sheet

CARDS = {
    "used": {
        "label": "USED PAPER",
        "hl": "hl-used",
        "num_color": "#1E88E5",
        "icon": USED_ICON,
        "mascot": "♻️",
    },
    "unused": {
        "label": "UNUSED PAPER",
        "hl": "hl-unused",
        "num_color": "#E53935",
        "icon": UNUSED_ICON,
        "mascot": "🗒️",
    },
}


def icon_row(icon_svg, count, max_icons=60):
    """Return HTML that shows the paper icon repeated `count` times."""
    shown = min(max(count, 0), max_icons)
    return icon_svg * shown


RAINBOW_PALETTE = ["#E53935", "#FB8C00", "#F9A825", "#43A047", "#1E88E5", "#8E24AA", "#00897B"]


def rainbow_title(text):
    """Return a list of (char, color) pairs for the rainbow header, spaces get no color."""
    letters = []
    i = 0
    for ch in text:
        if ch == " ":
            letters.append((ch, None))
        else:
            letters.append((ch, RAINBOW_PALETTE[i % len(RAINBOW_PALETTE)]))
            i += 1
    return letters


# ------------------------------------------------------------------
# Helper: make sure the DB is ready before handling a request
# ------------------------------------------------------------------
def ensure_db():
    """Return (client, error_message). error_message is None on success."""
    url, token = get_credentials()
    if not url or not token:
        return None, (
            "Database credentials are missing. "
            "Please add TURSO_DATABASE_URL and TURSO_AUTH_TOKEN to your .env file."
        )
    try:
        client = get_client()
        init_db(client)
        return client, None
    except Exception as error:
        return None, f"Could not connect to the database: {error}"


@app.context_processor
def inject_globals():
    return {"rainbow_title": rainbow_title("PAPER COUNTER")}


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
@app.route("/")
def home():
    client, error = ensure_db()
    if error:
        return render_template("error.html", message=error)

    data = load_data(client)
    used = data["used_paper"]
    unused = data["unused_paper"]

    cards = []
    for kind in ("used", "unused"):
        cfg = CARDS[kind]
        value = data[f"{kind}_paper"]
        cards.append(
            {
                "kind": kind,
                "label": cfg["label"],
                "hl": cfg["hl"],
                "num_color": cfg["num_color"],
                "mascot": cfg["mascot"],
                "value": value,
                "icons": icon_row(cfg["icon"], value),
            }
        )

    return render_template("home.html", active_page="Home", cards=cards)


@app.route("/update/<kind>/<action>", methods=["POST"])
def update(kind, action):
    if kind not in CARDS or action not in ("inc", "dec"):
        return redirect(url_for("home"))

    client, error = ensure_db()
    if error:
        return render_template("error.html", message=error)

    data = load_data(client)
    value = data[f"{kind}_paper"]

    if action == "inc":
        value += 1
    elif action == "dec" and value > 0:
        value -= 1

    data[f"{kind}_paper"] = value
    save_data(
        client,
        data["student_name"],
        data["machine_name"],
        data["used_paper"],
        data["unused_paper"],
    )

    return redirect(url_for("home"))


@app.route("/stats")
def stats():
    client, error = ensure_db()
    if error:
        return render_template("error.html", message=error)

    data = load_data(client)
    used = data["used_paper"]
    unused = data["unused_paper"]
    total = used + unused

    return render_template(
        "stats.html",
        active_page="Stats",
        used=used,
        unused=unused,
        total=total,
    )


@app.route("/settings", methods=["GET", "POST"])
def settings():
    client, error = ensure_db()
    if error:
        return render_template("error.html", message=error)

    data = load_data(client)

    if request.method == "POST":
        new_name = request.form.get("student_name", "").strip()
        new_machine = request.form.get("machine_name", "").strip()
        if new_name != data["student_name"] or new_machine != data["machine_name"]:
            data["student_name"] = new_name
            data["machine_name"] = new_machine
            save_data(
                client,
                data["student_name"],
                data["machine_name"],
                data["used_paper"],
                data["unused_paper"],
            )

    total = data["used_paper"] + data["unused_paper"]

    return render_template(
        "settings.html",
        active_page="Settings",
        student_name=data["student_name"],
        machine_name=data["machine_name"],
        total=total,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)
