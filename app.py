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
# Simple black-and-white styling
# ------------------------------------------------------------------
st.markdown(
    """
    <style>
    .card-title   { text-align:center; font-size:1.4rem; font-weight:700; color:#000; margin-bottom:0.4rem; }
    .card-number  { text-align:center; font-size:4rem;  font-weight:700; color:#000; margin:0.4rem 0 1rem 0; }
    .panel-title  { font-size:1.2rem; font-weight:700; color:#000; margin-bottom:0.6rem; }
    .panel-label  { font-size:0.9rem; color:#000; margin:0.6rem 0 0.1rem 0; }
    .total-number { font-size:2.6rem; font-weight:700; color:#000; text-align:center; margin:0; }
    .stButton > button {
        border:1px solid #000;
        border-radius:8px;
        background:#fff;
        color:#000;
        font-size:1.4rem;
        font-weight:700;
        padding:0.3rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<h2 style="text-align:center;color:#000;">Paper Counter</h2>',
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# Layout: two big cards on the left, a narrow info panel on the right
# ------------------------------------------------------------------
left_area, right_area = st.columns([3, 1])

with left_area:
    used_col, unused_col = st.columns(2)

    # ---------------- Used Paper card ----------------
    with used_col:
        card = st.container(border=True)
        with card:
            st.markdown('<p class="card-title">Used Paper</p>', unsafe_allow_html=True)
            st.markdown(
                f'<p class="card-number">{st.session_state.used_paper}</p>',
                unsafe_allow_html=True,
            )
            plus_col, minus_col = st.columns(2)

            if plus_col.button("+", key="used_plus", use_container_width=True):
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
        card = st.container(border=True)
        with card:
            st.markdown('<p class="card-title">Unused Paper</p>', unsafe_allow_html=True)
            st.markdown(
                f'<p class="card-number">{st.session_state.unused_paper}</p>',
                unsafe_allow_html=True,
            )
            plus_col, minus_col = st.columns(2)

            if plus_col.button("+", key="unused_plus", use_container_width=True):
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
    panel = st.container(border=True)
    with panel:
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
            f'<p class="total-number">{total_paper}</p>',
            unsafe_allow_html=True,
        )
