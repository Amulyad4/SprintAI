"""
Supabase data access layer — replaces SQLite qry/exe helpers.
All queries run with the authenticated user's JWT so RLS enforces per-user isolation.
"""
from datetime import datetime, timezone
import pandas as pd
from data.supabase_client import get_client


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _to_df(rows):
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _flatten_task(row):
    tm = row.pop("team_members", None) or {}
    sp = row.pop("sprints", None) or {}
    row["assignee_name"] = tm.get("name")
    row["velocity_avg"] = tm.get("velocity_avg")
    row["avatar_color"] = tm.get("avatar_color")
    row["sprint_status"] = sp.get("status")
    return row


def _flatten_tasks(rows):
    return [_flatten_task(dict(r)) for r in rows]


# ── reads ─────────────────────────────────────────────────────────────────────

def load_projects():
    r = get_client(require_auth=True).table("projects").select("*").order("id").execute()
    return _to_df(r.data)


def load_sprints(pid=None, status=None):
    q = get_client(require_auth=True).table("sprints").select("*")
    if pid is not None:
        q = q.eq("project_id", pid)
    if status:
        q = q.eq("status", status)
    r = q.order("id").execute()
    return _to_df(r.data)


def load_active(pid):
    r = (
        get_client(require_auth=True)
        .table("sprints")
        .select("*")
        .eq("project_id", pid)
        .eq("status", "Active")
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    return r.data[0] if r.data else None


def load_tasks(sprint_id=None, project_id=None, include_planning=False):
    q = (
        get_client(require_auth=True)
        .table("tasks")
        .select("*, team_members(name, velocity_avg, avatar_color), sprints(status)")
    )
    if sprint_id is not None:
        q = q.eq("sprint_id", sprint_id)
    if project_id is not None:
        q = q.eq("project_id", project_id)
    r = q.execute()
    rows = _flatten_tasks(r.data or [])
    if not include_planning:
        rows = [
            t for t in rows
            if t.get("sprint_id") is None
            or t.get("sprint_status") is None
            or t.get("sprint_status") != "Planning"
        ]
    return _to_df(rows)


def load_team(pid):
    r = (
        get_client(require_auth=True)
        .table("team_members")
        .select("*")
        .eq("project_id", pid)
        .order("id")
        .execute()
    )
    return _to_df(r.data)


def load_metrics(pid):
    sprints = load_sprints(pid=pid)
    if sprints.empty:
        return pd.DataFrame()
    sprint_ids = sprints["id"].tolist()
    r = (
        get_client(require_auth=True)
        .table("sprint_metrics")
        .select("*")
        .in_("sprint_id", sprint_ids)
        .execute()
    )
    df = _to_df(r.data)
    if df.empty:
        return df
    name_map = dict(zip(sprints["id"], sprints["name"]))
    pts_map = dict(zip(sprints["id"], sprints["planned_points"]))
    df["sprint_name"] = df["sprint_id"].map(name_map)
    df["planned_points"] = df["sprint_id"].map(pts_map)
    return df.sort_values("sprint_id")


def load_activity(pid, n=20):
    r = (
        get_client(require_auth=True)
        .table("activity_log")
        .select("*")
        .eq("project_id", pid)
        .order("id", desc=True)
        .limit(n)
        .execute()
    )
    return _to_df(r.data)


def load_backlog(pid):
    r = (
        get_client(require_auth=True)
        .table("tasks")
        .select("id, title, priority, story_points")
        .eq("project_id", pid)
        .execute()
    )
    rows = [t for t in (r.data or []) if not t.get("sprint_id")]
    return _to_df(rows)


def load_training_data(project_id):
    tasks = load_tasks(project_id=project_id, include_planning=True)
    if tasks.empty:
        return pd.DataFrame()
    sprints = load_sprints(pid=project_id, status="Completed")
    if sprints.empty:
        return pd.DataFrame()
    completed_sprint_ids = set(sprints["id"].tolist())
    df = tasks[
        tasks["actual_hours"].notna()
        & tasks["assignee_id"].notna()
        & tasks["sprint_id"].isin(completed_sprint_ids)
    ].copy()
    if df.empty:
        return pd.DataFrame()
    sprint_pts = sprints.set_index("id")[["planned_points", "completed_points"]]
    df = df.merge(
        sprint_pts, left_on="sprint_id", right_index=True, how="left", suffixes=("", "_sprint")
    )
    return df[["story_points", "estimated_hours", "actual_hours", "priority",
               "velocity_avg", "planned_points", "completed_points"]]


# ── writes ────────────────────────────────────────────────────────────────────

def create_project(name, description=""):
    r = (
        get_client(require_auth=True)
        .table("projects")
        .insert({"name": name, "description": description, "owner_id": st_user_id()})
        .execute()
    )
    return r.data[0]["id"] if r.data else None


def st_user_id():
    import streamlit as st
    uid = st.session_state.get("user_id")
    if not uid:
        raise RuntimeError("Not authenticated.")
    return uid


def update_task(task_id, **fields):
    fields["updated_at"] = _now_iso()
    get_client(require_auth=True).table("tasks").update(fields).eq("id", task_id).execute()


def create_task(**fields):
    r = get_client(require_auth=True).table("tasks").insert(fields).execute()
    return r.data[0]["id"] if r.data else None


def delete_task(task_id):
    get_client(require_auth=True).table("tasks").delete().eq("id", task_id).execute()


def create_sprint(**fields):
    r = get_client(require_auth=True).table("sprints").insert(fields).execute()
    return r.data[0]["id"] if r.data else None


def update_sprint(sprint_id, **fields):
    get_client(require_auth=True).table("sprints").update(fields).eq("id", sprint_id).execute()


def delete_sprint(sprint_id):
    client = get_client(require_auth=True)
    client.table("sprint_metrics").delete().eq("sprint_id", sprint_id).execute()
    client.table("tasks").update({"sprint_id": None}).eq("sprint_id", sprint_id).execute()
    client.table("sprints").delete().eq("id", sprint_id).execute()


def adjust_sprint_points(sprint_id, planned_delta=0, completed_delta=0):
    r = get_client(require_auth=True).table("sprints").select("planned_points, completed_points").eq("id", sprint_id).execute()
    if not r.data:
        return
    row = r.data[0]
    update_sprint(
        sprint_id,
        planned_points=max(0, int(row["planned_points"]) + planned_delta),
        completed_points=max(0, int(row["completed_points"]) + completed_delta),
    )


def upsert_sprint_metrics(sprint_id, **fields):
    fields["sprint_id"] = sprint_id
    get_client(require_auth=True).table("sprint_metrics").upsert(fields, on_conflict="sprint_id").execute()


def clear_sprint_tasks(sprint_id):
    get_client(require_auth=True).table("tasks").update({"sprint_id": None}).eq("sprint_id", sprint_id).neq("status", "Done").execute()


def assign_task_to_sprint(task_id, sprint_id, story_points):
    client = get_client(require_auth=True)
    client.table("tasks").update({"sprint_id": sprint_id}).eq("id", task_id).execute()
    adjust_sprint_points(sprint_id, planned_delta=int(story_points))


def create_team_member(**fields):
    r = get_client(require_auth=True).table("team_members").insert(fields).execute()
    return r.data[0]["id"] if r.data else None


def update_team_member(member_id, **fields):
    get_client(require_auth=True).table("team_members").update(fields).eq("id", member_id).execute()


def delete_team_member(member_id):
    client = get_client(require_auth=True)
    client.table("tasks").update({"assignee_id": None}).eq("assignee_id", member_id).execute()
    client.table("team_members").delete().eq("id", member_id).execute()


def reconcile_sprint_points(pid):
    sprints = load_sprints(pid=pid)
    if sprints.empty:
        return
    tasks = load_tasks(project_id=pid, include_planning=True)
    for _, sprint in sprints.iterrows():
        sid = int(sprint["id"])
        stasks = tasks[tasks["sprint_id"] == sid] if not tasks.empty else pd.DataFrame()
        planned = int(stasks["story_points"].sum()) if not stasks.empty else 0
        completed = int(stasks.loc[stasks["status"] == "Done", "story_points"].sum()) if not stasks.empty else 0
        update_sprint(sid, planned_points=planned, completed_points=completed)
