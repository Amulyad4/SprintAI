"""
Supabase client factory — authenticated per Streamlit session.
"""
import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()


def _credentials():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_ANON_KEY", "")
    if not url and "SUPABASE_URL" in st.secrets:
        url = st.secrets["SUPABASE_URL"]
    if not key and "SUPABASE_ANON_KEY" in st.secrets:
        key = st.secrets["SUPABASE_ANON_KEY"]
    return url, key


def get_client(*, require_auth=False):
    """Return a Supabase client with the current user's JWT when available."""
    url, key = _credentials()
    if not url or not key:
        raise RuntimeError("Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_ANON_KEY.")
    if str(key).startswith("http"):
        raise RuntimeError("SUPABASE_ANON_KEY looks invalid (should be an API key, not a URL).")

    client = create_client(url, key)
    access = st.session_state.get("access_token")
    refresh = st.session_state.get("refresh_token")
    if access and refresh:
        try:
            client.auth.set_session(access, refresh)
        except Exception:
            pass
    elif require_auth:
        raise RuntimeError("Not authenticated.")
    return client
