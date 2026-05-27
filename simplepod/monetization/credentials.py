"""Streamlit credentials/password manager for monetization swarm."""

import base64
import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime

import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CREDENTIALS_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "tools",
    "saved_sessions",
    "monetization_credentials.json",
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Credential:
    id: str
    website: str
    url: str
    username: str
    password: str  # base64-encoded when stored
    notes: str
    created_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_dir(path: str) -> None:
    """Ensure the parent directory for *path* exists."""
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _encode_password(password: str) -> str:
    """Simple base64 obfuscation for passwords at rest."""
    return base64.b64encode(password.encode("utf-8")).decode("utf-8")


def _decode_password(encoded: str) -> str:
    """Decode a base64-obfuscated password."""
    return base64.b64decode(encoded.encode("utf-8")).decode("utf-8")


def _load_credentials() -> list[Credential]:
    """Load credentials from disk; return an empty list if missing or invalid."""
    if not os.path.exists(CREDENTIALS_PATH):
        return []
    try:
        with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    credentials: list[Credential] = []
    for item in raw:
        try:
            credentials.append(Credential(**item))
        except TypeError:
            continue
    return credentials


def _save_credentials(credentials: list[Credential]) -> None:
    """Persist credentials to disk."""
    _ensure_dir(CREDENTIALS_PATH)
    with open(CREDENTIALS_PATH, "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in credentials], f, indent=2)


def _csv_content(credentials: list[Credential]) -> str:
    """Generate CSV text from credentials (passwords decoded)."""
    lines = ["id,website,url,username,password,notes,created_at"]
    for c in credentials:
        decoded_pw = _decode_password(c.password)
        lines.append(
            f'"{c.id}","{c.website}","{c.url}","{c.username}",'
            f'"{decoded_pw}","{c.notes}","{c.created_at}"'
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def render_credentials() -> None:
    """Render the credentials manager page."""
    st.title("🔐 Monetization Credentials")
    st.caption("Securely store and manage website logins for the monetization swarm.")

    # -----------------------------------------------------------------------
    # Session state for delete confirmation
    # -----------------------------------------------------------------------
    if "delete_target" not in st.session_state:
        st.session_state.delete_target = None

    credentials = _load_credentials()

    # -----------------------------------------------------------------------
    # Add new credential form
    # -----------------------------------------------------------------------
    with st.expander("➕ Add New Credential", expanded=False):
        with st.form("add_credential_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                website = st.text_input("Website Name", placeholder="Stripe")
                url = st.text_input("URL", placeholder="https://dashboard.stripe.com")
            with col2:
                username = st.text_input("Username / Email", placeholder="user@example.com")
                password = st.text_input("Password", type="password")
            notes = st.text_area("Notes (optional)", placeholder="2FA enabled, API keys...")

            submitted = st.form_submit_button("💾 Save Credential")
            if submitted:
                if not website or not url or not username or not password:
                    st.error("Please fill out all required fields.")
                else:
                    new_credential = Credential(
                        id=str(uuid.uuid4()),
                        website=website.strip(),
                        url=url.strip(),
                        username=username.strip(),
                        password=_encode_password(password),
                        notes=notes.strip(),
                        created_at=datetime.now().isoformat(),
                    )
                    credentials.append(new_credential)
                    _save_credentials(credentials)
                    st.success(f"Credential for **{website}** saved successfully!")
                    st.rerun()

    # -----------------------------------------------------------------------
    # Import / Export JSON
    # -----------------------------------------------------------------------
    with st.expander("📤 Import / Export JSON", expanded=False):
        ie_col1, ie_col2 = st.columns(2)

        with ie_col1:
            st.markdown("**Export JSON**")
            export_data = json.dumps([asdict(c) for c in credentials], indent=2)
            st.download_button(
                label="📥 Download JSON",
                data=export_data,
                file_name="monetization_credentials.json",
                mime="application/json",
            )

        with ie_col2:
            st.markdown("**Import JSON**")
            uploaded_file = st.file_uploader(
                "Upload credentials JSON",
                type=["json"],
                key="import_json",
            )
            if uploaded_file is not None:
                try:
                    imported_raw = json.load(uploaded_file)
                    if not isinstance(imported_raw, list):
                        raise ValueError("JSON must be a list of credential objects.")

                    imported: list[Credential] = []
                    for item in imported_raw:
                        if "id" not in item:
                            item["id"] = str(uuid.uuid4())
                        if "created_at" not in item:
                            item["created_at"] = datetime.now().isoformat()
                        imported.append(Credential(**item))

                    # Merge imported credentials (avoid exact duplicates by id)
                    existing_ids = {c.id for c in credentials}
                    merged = credentials.copy()
                    for c in imported:
                        if c.id not in existing_ids:
                            merged.append(c)
                    _save_credentials(merged)
                    st.success(f"Imported {len(imported)} credential(s).")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Import failed: {exc}")

    # -----------------------------------------------------------------------
    # Export to CSV
    # -----------------------------------------------------------------------
    if credentials:
        st.download_button(
            label="📄 Export to CSV",
            data=_csv_content(credentials),
            file_name="monetization_credentials.csv",
            mime="text/csv",
        )

    st.divider()

    # -----------------------------------------------------------------------
    # Saved credentials list
    # -----------------------------------------------------------------------
    if not credentials:
        st.info("No credentials saved yet. Use the form above to add your first login.")
        return

    st.subheader(f"Saved Credentials ({len(credentials)})")

    for cred in credentials:
        with st.container(border=True):
            top_col, action_col = st.columns([4, 1])

            with top_col:
                st.markdown(f"### [{cred.website}]({cred.url})")
                st.markdown(f"**Username:** `{cred.username}`")
                if cred.notes:
                    st.markdown(f"_{cred.notes}_")
                st.caption(f"Created: {cred.created_at}")

            with action_col:
                # Toggle to show/hide password
                show_key = f"show_pw_{cred.id}"
                if show_key not in st.session_state:
                    st.session_state[show_key] = False

                if st.toggle(
                    "👁️ Show Password",
                    key=show_key,
                    value=st.session_state[show_key],
                ):
                    st.code(_decode_password(cred.password), language="text")

                # Delete button
                delete_key = f"delete_{cred.id}"
                if st.button("🗑️ Delete", key=delete_key, use_container_width=True):
                    st.session_state.delete_target = cred.id
                    st.rerun()

            # Handle deletion confirmation
            if st.session_state.delete_target == cred.id:
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button(
                        "✅ Confirm Delete",
                        key=f"confirm_{cred.id}",
                        use_container_width=True,
                    ):
                        updated = [c for c in credentials if c.id != cred.id]
                        _save_credentials(updated)
                        st.session_state.delete_target = None
                        st.success(f"Deleted credential for **{cred.website}**.")
                        st.rerun()
                with cancel_col:
                    if st.button(
                        "❌ Cancel",
                        key=f"cancel_{cred.id}",
                        use_container_width=True,
                    ):
                        st.session_state.delete_target = None
                        st.rerun()
