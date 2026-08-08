import streamlit as st
import libsql_client
from datetime import datetime

# ------------------------------------------------------------------
# Page setup
# ------------------------------------------------------------------
st.set_page_config(page_title="Paper Counter", layout="wide")


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

    # Is there already a record?
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
        [
            student_name,
            machine_name,
            used_paper,
            unused_paper,
            datetime.now().isoformat(),
        ],
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

# ------------------------------------------------------------------
# Styling (self-contained colors, so it looks the same in any theme)
# ------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* App background */
    .stApp { background-color: #FDF2F8; }

    /* Card look for every bordered container */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF;
        border: 1px solid #F3D6E4;
        border-radius: 16px;
        padding: 6px 10px;
        box-shadow: 0 1px 3px rgba(131, 24, 67, 0.07);
    }

    /* Page title */
    .page-title {
        text-align: center;
        font-size: 2.4rem;
        font-weight: 800;
        color: #831843;
        letter-spacing: -0.5px;
        margin: 0.2rem 0 1.4rem 0;
    }

    /* Row of paper icons (one icon per count) */
    .icon-row {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 6px;
        min-height: 40px;
        margin: 0.5rem 0 0.2rem 0;
    }
    .icon-row svg { width: 30px; height: 30px; }

    /* Card text */
    .card-title {
        text-align: center;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: #A25C86;
        margin: 0.4rem 0 0.2rem 0;
    }
    .card-number {
        text-align: center;
        font-size: 4rem;
        font-weight: 800;
        color: #DB2777;
        line-height: 1.1;
        margin: 0 0 0.8rem 0;
    }

    /* Right info panel */
    .panel-title {
        font-size: 1.1rem;
        font-weight: 800;
        color: #831843;
        margin: 0.2rem 0 0.8rem 0;
    }
    .panel-label {
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: #A25C86;
        margin: 0.8rem 0 0.2rem 0;
    }
    .total-box {
        background: #FCE7F3;
        border-radius: 12px;
        padding: 0.6rem;
        text-align: center;
        margin-top: 0.3rem;
    }
    .total-number {
        font-size: 2.4rem;
        font-weight: 800;
        color: #DB2777;
        margin: 0;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 10px;
        font-size: 1.3rem;
        font-weight: 700;
        padding: 0.35rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Small paper icons drawn with inline SVG (no image files needed).
# UNUSED = a blank clean sheet. USED = a sheet with written lines on it.
UNUSED_ICON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="#DB2777" stroke-width="1.6" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
    '<path d="M14 2v6h6"/></svg>'
)
USED_ICON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="#DB2777" stroke-width="1.6" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
    '<path d="M14 2v6h6"/>'
    '<line x1="8" y1="9" x2="11" y2="9"/>'
    '<line x1="8" y1="13" x2="16" y2="13"/>'
    '<line x1="8" y1="17" x2="16" y2="17"/></svg>'
)


def icon_row(icon_svg, count, max_icons=60):
    """Return HTML that shows the paper icon repeated `count` times."""
    shown = min(max(count, 0), max_icons)   # never below 0, and cap for safety
    return f'<div class="icon-row">{icon_svg * shown}</div>'


st.markdown('<div class="page-title">Paper Counter</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------
# Layout: two big cards on the left, a narrow info panel on the right
# ------------------------------------------------------------------
left_area, right_area = st.columns([3, 1])

with left_area:
    used_col, unused_col = st.columns(2)

    # ---------------- Used Paper card ----------------
    with used_col:
        with st.container(border=True):
            st.markdown(icon_row(USED_ICON, st.session_state.used_paper), unsafe_allow_html=True)
            st.markdown('<p class="card-title">Used Paper</p>', unsafe_allow_html=True)
            st.markdown(
                f'<p class="card-number">{st.session_state.used_paper}</p>',
                unsafe_allow_html=True,
            )
            plus_col, minus_col = st.columns(2)

            if plus_col.button("+", key="used_plus", use_container_width=True, type="primary"):
                st.session_state.used_paper += 1
                save_data(
                    client,
                    st.session_state.student_name,
                    st.session_state.machine_name,
                    st.session_state.used_paper,
                    st.session_state.unused_paper,
                )
                st.rerun()

            if minus_col.button("-", key="used_minus", use_container_width=True):
                if st.session_state.used_paper > 0:
                    st.session_state.used_paper -= 1
                    save_data(
                        client,
                        st.session_state.student_name,
                        st.session_state.machine_name,
                        st.session_state.used_paper,
                        st.session_state.unused_paper,
                    )
                    st.rerun()

    # ---------------- Unused Paper card ----------------
    with unused_col:
        with st.container(border=True):
            st.markdown(icon_row(UNUSED_ICON, st.session_state.unused_paper), unsafe_allow_html=True)
            st.markdown('<p class="card-title">Unused Paper</p>', unsafe_allow_html=True)
            st.markdown(
                f'<p class="card-number">{st.session_state.unused_paper}</p>',
                unsafe_allow_html=True,
            )
            plus_col, minus_col = st.columns(2)

            if plus_col.button("+", key="unused_plus", use_container_width=True, type="primary"):
                st.session_state.unused_paper += 1
                save_data(
                    client,
                    st.session_state.student_name,
                    st.session_state.machine_name,
                    st.session_state.used_paper,
                    st.session_state.unused_paper,
                )
                st.rerun()

            if minus_col.button("-", key="unused_minus", use_container_width=True):
                if st.session_state.unused_paper > 0:
                    st.session_state.unused_paper -= 1
                    save_data(
                        client,
                        st.session_state.student_name,
                        st.session_state.machine_name,
                        st.session_state.used_paper,
                        st.session_state.unused_paper,
                    )
                    st.rerun()

# ---------------- Right side information panel ----------------
with right_area:
    with st.container(border=True):
        st.markdown('<p class="panel-title">Information</p>', unsafe_allow_html=True)

        new_name = st.text_input("Student Name", value=st.session_state.student_name)
        new_machine = st.text_input("Machine Name", value=st.session_state.machine_name)

        # If the name or machine changed, save it right away
        if (
            new_name != st.session_state.student_name
            or new_machine != st.session_state.machine_name
        ):
            st.session_state.student_name = new_name
            st.session_state.machine_name = new_machine
            save_data(
                client,
                st.session_state.student_name,
                st.session_state.machine_name,
                st.session_state.used_paper,
                st.session_state.unused_paper,
            )

        total_paper = st.session_state.used_paper + st.session_state.unused_paper
        st.markdown('<p class="panel-label">Total Paper</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="total-box"><p class="total-number">{total_paper}</p></div>',
            unsafe_allow_html=True,
        )
