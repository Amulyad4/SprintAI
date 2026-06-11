"""
auth.py
Supabase authentication helpers for Streamlit.
"""
import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
from data.db_setup import seed_data_if_empty

load_dotenv()


def _get_supabase_client():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_ANON_KEY", "")

    if not url and "SUPABASE_URL" in st.secrets:
        url = st.secrets["SUPABASE_URL"]
    if not key and "SUPABASE_ANON_KEY" in st.secrets:
        key = st.secrets["SUPABASE_ANON_KEY"]

    if not url or not key:
        return None, "Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_ANON_KEY."
    if str(key).startswith("http"):
        return None, "SUPABASE_ANON_KEY looks invalid (it should be a long API key, not a URL)."

    try:
        return create_client(url, key), ""
    except Exception as exc:
        return None, f"Supabase client init failed: {exc}"


def _store_session(resp):
    user = getattr(resp, "user", None)
    session = getattr(resp, "session", None)
    if not user or not session:
        return None

    user_meta = getattr(user, "user_metadata", {}) or {}
    role = user_meta.get("role", "Member")
    full_name = user_meta.get("full_name") or user_meta.get("display_name")

    st.session_state["user"] = user.email
    st.session_state["user_id"] = user.id
    st.session_state["user_name"] = full_name
    st.session_state["role"] = role if role in ("Manager", "Member") else "Member"
    st.session_state["access_token"] = session.access_token
    st.session_state["refresh_token"] = session.refresh_token
    return user


def signup_user(username, password, role="Member"):
    username = (username or "").strip()
    password = (password or "").strip()
    role = role if role in ("Manager", "Member") else "Member"

    if not username or not password:
        return False, "Username and password are required."
    if "@" not in username:
        return False, "For Supabase auth, Username must be a valid email address."

    client, err = _get_supabase_client()
    if not client:
        return False, err

    try:
        resp = client.auth.sign_up(
            {
                "email": username,
                "password": password,
                "options": {"data": {"role": role, "display_name": username.split("@")[0]}},
            }
        )
        user = _store_session(resp)
        if user:
            pass
        return True, "Signup successful. Please login."
    except Exception as exc:
        return False, f"Signup failed: {exc}"


def login_user(username, password):
    username = (username or "").strip()
    password = (password or "").strip()
    if not username or not password:
        return False, "Username and password are required."

    client, err = _get_supabase_client()
    if not client:
        return False, err

    try:
        resp = client.auth.sign_in_with_password({"email": username, "password": password})
    except Exception as exc:
        err = str(exc)
        if "Email not confirmed" in err or "email not confirmed" in err:
            return False, (
                "Login failed: email not confirmed. Please verify your email first, "
                "or disable email confirmation in Supabase Auth settings for local development."
            )
        return False, f"Login failed: {err}"

    user = _store_session(resp)
    if not user:
        return False, "Invalid username or password."
    try:
        from data.supabase_client import get_client

        client = get_client()

        tm = (
            client.table("team_members")
            .select("*")
            .eq("email", user.email)
            .execute()
        )
        st.write("USER EMAIL:", user.email)
        st.write("TEAM MEMBER DATA:", tm.data)

        if tm.data:
            member = tm.data[0]

            st.write("MATCH FOUND:", member)

            client.table("team_members").update(
                {"user_id": user.id}
            ).eq("id", member["id"]).execute()

            st.success("UPDATED USER_ID")

            st.session_state["team_member_id"] = member["id"]
    except Exception as e:
        st.error(f"ERROR: {e}")
    pass

    return True, "Login successful."


def logout_user():
    client, _ = _get_supabase_client()
    if client and st.session_state.get("access_token"):
        try:
            client.auth.set_session(
                st.session_state["access_token"],
                st.session_state.get("refresh_token", ""),
            )
            client.auth.sign_out()
        except Exception:
            pass
    for key in (
        "user",
        "user_id",
        "user_name",
        "role",
        "team_member_id",
        "access_token",
        "refresh_token"
    ):
        st.session_state[key] = None
    return True
