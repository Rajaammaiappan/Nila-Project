import streamlit as st
import libsql_client
import pandas as pd
import altair as alt
from datetime import datetime

# ------------------------------------------------------------------
# Page setup
# ------------------------------------------------------------------
st.set_page_config(page_title="Paper Counter", page_icon="📄", layout="wide")


# ------------------------------------------------------------------
# Read the database credentials from Streamlit secrets
# ------------------------------------------------------------------
def get_credentials():
    """Return (url, token) from st.secrets, or (None, None) if missing."""
    try:
        url = st.secrets["TURSO_DATABASE_URL"]
        token = st.secrets["TURSO_AUTH_TOKEN"]
        return url, token
    except (KeyError, FileNotFoundError):
        return None, None


# ------------------------------------------------------------------
# Create ONE database client and reuse it (cached, so we connect once)
# ------------------------------------------------------------------
@st.cache_resource
def get_client(url, token):
    """Create and return a Turso client."""
    # The sync client turns libsql:// into a websocket (wss://) that Turso
    # rejects. Switching to https:// makes it use HTTP, which works.
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "https://", 1)
    return libsql_client.create_client_sync(url=url, auth_token=token)


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
# Stop early if the secrets are missing
# ------------------------------------------------------------------
url, token = get_credentials()
if not url or not token:
    st.error(
        "Database credentials are missing. "
        "Please add TURSO_DATABASE_URL and TURSO_AUTH_TOKEN to your Streamlit secrets."
    )
    st.stop()

# ------------------------------------------------------------------
# Connect and prepare the database
# ------------------------------------------------------------------
try:
    client = get_client(url, token)
    init_db(client)
except Exception as error:
    st.error(f"Could not connect to the database: {error}")
    st.stop()

# ------------------------------------------------------------------
# Load the data one time into session_state
# ------------------------------------------------------------------
if "loaded" not in st.session_state:
    data = load_data(client)
    st.session_state.student_name = data["student_name"]
    st.session_state.machine_name = data["machine_name"]
    st.session_state.used_paper = data["used_paper"]
    st.session_state.unused_paper = data["unused_paper"]
    st.session_state.loaded = True

# Which page is open right now (Home / Stats / Settings)
if "page" not in st.session_state:
    st.session_state.page = "Home"


def persist():
    """Save every current value to the database."""
    save_data(
        client,
        st.session_state.student_name,
        st.session_state.machine_name,
        st.session_state.used_paper,
        st.session_state.unused_paper,
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


def icon_row(icon_svg, count, max_icons=60):
    """Return HTML that shows the paper icon repeated `count` times."""
    shown = min(max(count, 0), max_icons)
    return f'<div class="icon-row">{icon_svg * shown}</div>'


# ------------------------------------------------------------------
# Styling
# ------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap');

    html, body, [class*="css"], .stMarkdown, button, input {
        font-family: 'Patrick Hand', 'Comic Sans MS', cursive;
    }
    .stApp { background-color: #FFFDF7; }

    /* Base card */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 22px;
        padding: 12px 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    /* Green card for USED, blue card for UNUSED */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.tag-used) {
        background: #F5FBE8 !important;
        border: 2px solid #7CB342 !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.tag-unused) {
        background: #EAF3FF !important;
        border: 2px solid #4A90D9 !important;
    }
    .tag-used, .tag-unused, .nav-bar { display:none; }

    /* Pink bottom navigation bar */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.nav-bar) {
        background: #F8D3E6 !important;
        border: 2px solid #E79FC2 !important;
        margin-top: 20px;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.nav-bar) .stButton > button {
        background: transparent;
        border: none;
        box-shadow: none;
        color: #6A1B9A;
        font-size: 1.15rem;
        font-weight: 700;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.nav-bar) .stButton > button:hover {
        background: #F3BFD8;
        color: #4A148C;
    }

    /* Rainbow title */
    .page-title {
        text-align: center;
        font-size: 3rem;
        font-weight: 700;
        letter-spacing: 2px;
        margin: 0.2rem 0 1.2rem 0;
    }

    /* Highlighted labels */
    .label-wrap { text-align: center; margin: 0.2rem 0 0.5rem 0; }
    .hl-used, .hl-unused {
        font-size: 1.7rem;
        padding: 2px 16px;
        border-radius: 12px;
        color: #222;
    }
    .hl-used   { background: #FFE066; }
    .hl-unused { background: #7EC8F3; }

    /* Mascot emoji */
    .mascot { font-size: 3.4rem; text-align: center; margin-top: 0.4rem; }

    /* Big number */
    .big-number {
        text-align: center;
        font-size: 4.2rem;
        font-weight: 700;
        line-height: 1;
        margin: 0.2rem 0 0.5rem 0;
    }

    /* Icon pile */
    .icon-row {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 6px;
        min-height: 40px;
        margin: 0.4rem 0;
    }
    .icon-row svg { width: 30px; height: 30px; }

    /* Section titles */
    .section-title {
        text-align: center;
        font-size: 1.8rem;
        font-weight: 700;
        color: #6A1B9A;
        margin: 0.4rem 0 1rem 0;
    }

    /* Buttons (general) */
    .stButton > button {
        border-radius: 14px;
        font-size: 1.5rem;
        font-weight: 700;
        padding: 0.3rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# Rainbow header title
# ------------------------------------------------------------------
_palette = ["#E53935", "#FB8C00", "#F9A825", "#43A047", "#1E88E5", "#8E24AA", "#00897B"]
_letters = ""
_i = 0
for _ch in "PAPER COUNTER":
    if _ch == " ":
        _letters += '<span style="display:inline-block;width:18px;"></span>'
    else:
        _letters += f'<span style="color:{_palette[_i % len(_palette)]}">{_ch}</span>'
        _i += 1
st.markdown(f'<div class="page-title">{_letters}</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------
# Per-card settings
# ------------------------------------------------------------------
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


def render_card(kind):
    """Draw one colored card with mascot, number, icon pile, and + / - buttons."""
    cfg = CARDS[kind]
    state_key = f"{kind}_paper"

    with st.container(border=True):
        st.markdown(f'<span class="tag-{kind}"></span>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="label-wrap"><span class="{cfg["hl"]}">{cfg["label"]}</span></div>',
            unsafe_allow_html=True,
        )

        left, middle, right = st.columns([1, 2, 2])

        with left:
            st.markdown(f'<div class="mascot">{cfg["mascot"]}</div>', unsafe_allow_html=True)

        with middle:
            number_ph = st.empty()          # filled after the buttons are handled
            b_plus, b_minus = st.columns(2)
            clicked_plus = b_plus.button("＋", key=f"{kind}_plus",
                                         use_container_width=True, type="primary")
            clicked_minus = b_minus.button("－", key=f"{kind}_minus",
                                           use_container_width=True)

        with right:
            pile_ph = st.empty()

        if clicked_plus:
            st.session_state[state_key] += 1
            persist()
        if clicked_minus and st.session_state[state_key] > 0:
            st.session_state[state_key] -= 1
            persist()

        value = st.session_state[state_key]
        number_ph.markdown(
            f'<div class="big-number" style="color:{cfg["num_color"]}">{value}</div>',
            unsafe_allow_html=True,
        )
        pile_ph.markdown(icon_row(cfg["icon"], value), unsafe_allow_html=True)


# ------------------------------------------------------------------
# Page renderers
# ------------------------------------------------------------------
def render_home():
    render_card("used")
    st.write("")
    render_card("unused")


def render_stats():
    st.markdown('<div class="section-title">📊 Paper Breakdown</div>', unsafe_allow_html=True)

    used = st.session_state.used_paper
    unused = st.session_state.unused_paper
    total = used + unused

    if total == 0:
        st.info("Add some paper on the Home page to see the pie chart.")
        return

    source = pd.DataFrame(
        {"Type": ["Used Paper", "Unused Paper"], "Count": [used, unused]}
    )
    pie = (
        alt.Chart(source)
        .mark_arc(innerRadius=0, stroke="#FFFFFF", strokeWidth=2)
        .encode(
            theta=alt.Theta("Count:Q"),
            color=alt.Color(
                "Type:N",
                scale=alt.Scale(
                    domain=["Used Paper", "Unused Paper"],
                    range=["#7CB342", "#4A90D9"],
                ),
                legend=alt.Legend(title=""),
            ),
            tooltip=["Type", "Count"],
        )
        .properties(height=340)
    )
    st.altair_chart(pie, use_container_width=True)

    st.markdown(
        f'<p style="text-align:center;font-size:1.3rem;">'
        f"Total paper: <b>{total}</b> &nbsp;•&nbsp; "
        f'Used: <b style="color:#7CB342">{used}</b> &nbsp;•&nbsp; '
        f'Unused: <b style="color:#4A90D9">{unused}</b></p>',
        unsafe_allow_html=True,
    )


def render_settings():
    st.markdown('<div class="section-title">⚙️ Settings</div>', unsafe_allow_html=True)

    new_name = st.text_input("Student Name", value=st.session_state.student_name)
    new_machine = st.text_input("Machine Name", value=st.session_state.machine_name)

    if (
        new_name != st.session_state.student_name
        or new_machine != st.session_state.machine_name
    ):
        st.session_state.student_name = new_name
        st.session_state.machine_name = new_machine
        persist()

    total = st.session_state.used_paper + st.session_state.unused_paper
    st.markdown(
        f'<p style="font-size:1.3rem;margin-top:1rem;">Total Paper: <b>{total}</b></p>',
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------
# Show the current page (Home has NO pie chart, only the two cards)
# ------------------------------------------------------------------
if st.session_state.page == "Home":
    render_home()
elif st.session_state.page == "Stats":
    render_stats()
elif st.session_state.page == "Settings":
    render_settings()

# ------------------------------------------------------------------
# Bottom navigation bar
# ------------------------------------------------------------------
with st.container(border=True):
    st.markdown('<span class="nav-bar"></span>', unsafe_allow_html=True)
    nav_cols = st.columns(3)
    pages = [("🏠 Home", "Home"), ("📊 Stats", "Stats"), ("⚙️ Settings", "Settings")]
    for col, (label, page_id) in zip(nav_cols, pages):
        active = st.session_state.page == page_id
        shown = ("• " + label) if active else label
        if col.button(shown, key=f"nav_{page_id}", use_container_width=True):
            st.session_state.page = page_id
            st.rerun()
