"""
db_setup.py — Per-user demo seed data and activity logging via Supabase.
"""
import random
from data.supabase_client import get_client


def log_activity(project_id, actor, action, task_title="", field_changed="",
                 old_value="", new_value="", task_id=None, sprint_id=None):

    get_client(require_auth=True).table("activity_log").insert({
        "project_id": int(project_id) if project_id is not None else None,
        "sprint_id": int(sprint_id) if sprint_id is not None else None,
        "task_id": int(task_id) if task_id is not None else None,
        "task_title": str(task_title),
        "actor": str(actor),
        "action": str(action),
        "field_changed": str(field_changed),
        "old_value": str(old_value),
        "new_value": str(new_value),
    }).execute()


def seed_data_if_empty(user_id, display_name=None):
    """
    Seed a private demo project for this user only (skipped if they already have projects).
    Each authenticated user gets their own isolated copy via RLS owner_id.
    """
    client = get_client(require_auth=True)
    existing = client.table("projects").select("id").eq("owner_id", user_id).limit(1).execute()
    if existing.data:
        return

    member_label = (display_name or "You").strip() or "You"

    proj = client.table("projects").insert({
        "owner_id": user_id,
        "name": "AI Sprint Manager",
        "description": "CVR College IOMP Project — Batch 19",
    }).execute()
    pid = proj.data[0]["id"]

    colors = ["#ec4899", "#3b82f6", "#10b981", "#f59e0b"]
    team = [
        (member_label, "Full Stack Developer", 14.5, colors[0]),
        ("K. Amulya", "Frontend Developer", 14.5, colors[0]),
        ("M. Bhavani", "ML Engineer", 16.0, colors[1]),
        ("B.G.L. Santhoshi", "Backend Developer", 15.0, colors[2]),
        ("Mr. Sudheer", "Supervisor/QA", 12.0, colors[3]),
    ]
    mids = []
    for name, role, vel, col in team:
        row = client.table("team_members").insert({
            "name": name, "role": role, "velocity_avg": vel,
            "project_id": pid, "avatar_color": col,
        }).execute()
        mids.append(row.data[0]["id"])

    sprints_data = [
        ("Sprint 1", "Set up base infrastructure", "2025-01-06", "2025-01-17", "Completed", 36, 30),
        ("Sprint 2", "Implement core task management", "2025-01-20", "2025-01-31", "Completed", 42, 40),
        ("Sprint 3", "ML model integration", "2025-02-03", "2025-02-14", "Completed", 40, 38),
        ("Sprint 4", "Dashboard & analytics", "2025-02-17", "2025-02-28", "Completed", 44, 44),
    ]
    task_templates = [
        ("Set up project repo", "High", "Story", 3, 6, 5.5),
        ("Design database schema", "High", "Task", 5, 10, 11),
        ("Build REST API endpoints", "Critical", "Story", 8, 16, 18),
        ("Implement user auth", "High", "Task", 5, 10, 9.5),
        ("Write unit tests", "Medium", "Task", 3, 6, 6.5),
        ("Data preprocessing module", "High", "Story", 5, 10, 10),
        ("Train ML prediction model", "Critical", "Story", 8, 16, 17),
        ("Sprint report generator", "Medium", "Task", 3, 6, 5),
        ("UI dashboard component", "High", "Story", 5, 10, 12),
        ("Integrate Scikit-learn", "High", "Task", 5, 10, 10),
        ("Risk detection logic", "Critical", "Story", 8, 16, 15),
        ("Streamlit frontend pages", "High", "Task", 5, 10, 9),
    ]
    for i, (sname, goal, sd, ed, stat, pp, cp) in enumerate(sprints_data):
        spr = client.table("sprints").insert({
            "project_id": pid, "name": sname, "goal": goal,
            "start_date": sd, "end_date": ed, "status": stat,
            "planned_points": pp, "completed_points": cp,
        }).execute()
        sid = spr.data[0]["id"]
        for j in range(4):
            t = task_templates[(i * 3 + j) % len(task_templates)]
            title, pri, itype, sp, est, act = t
            status = "Done" if random.random() > 0.2 else "In Progress"
            client.table("tasks").insert({
                "sprint_id": sid, "project_id": pid, "title": title,
                "assignee_id": mids[j % len(mids)], "priority": pri, "status": status,
                "issue_type": itype, "story_points": sp, "estimated_hours": est,
                "actual_hours": round(act + random.uniform(-1, 2), 1),
                "tags": "ml,backend", "updated_at": ed,
            }).execute()
            client.table("activity_log").insert({
                "project_id": pid, "sprint_id": sid, "task_title": title,
                "actor": "System", "action": "created", "field_changed": "status", "new_value": "Todo",
            }).execute()
        client.table("sprint_metrics").insert({
            "sprint_id": sid, "velocity": cp,
            "completion_rate": round(cp / pp * 100, 1),
            "avg_cycle_time": round(random.uniform(1.5, 3.5), 2),
            "blockers_count": random.randint(0, 3),
            "on_time_tasks": random.randint(2, 4),
            "late_tasks": random.randint(0, 2),
        }).execute()

    # Active Sprint 5
    spr5 = client.table("sprints").insert({
        "project_id": pid, "name": "Sprint 5",
        "goal": "AI recommendations & reporting",
        "start_date": "2026-03-01", "end_date": "2026-03-14",
        "status": "Active", "planned_points": 40, "completed_points": 18,
    }).execute()
    asid = spr5.data[0]["id"]
    active_tasks = [
        ("NLP user story parser", "Critical", "Story", 8, 16, None, 0, "In Progress", "nlp,ml", None),
        ("Recommendation engine", "High", "Story", 5, 10, None, 1, "In Progress", "ml", None),
        ("Automated retrospective", "High", "Task", 5, 10, None, 2, "Todo", "reporting", None),
        ("Streamlit UI polish", "Medium", "Task", 3, 6, 5.5, 3, "Done", "ui", None),
        ("Integration tests", "High", "Task", 5, 10, None, 0, "Blocked", "testing", "Waiting for NLP model"),
        ("Performance benchmarking", "Low", "Task", 2, 4, None, 1, "Todo", "ml", None),
        ("Deploy on local server", "High", "Story", 5, 10, None, 2, "In Progress", "devops", None),
        ("Sprint 5 demo prep", "Medium", "Task", 3, 6, None, 3, "Todo", "docs", None),
    ]
    actor_names = [member_label, "K. Amulya", "M. Bhavani", "B.G.L. Santhoshi", "Mr. Sudheer"]
    for title, pri, itype, sp, est, act, midx, status, tags, blk in active_tasks:
        client.table("tasks").insert({
            "sprint_id": asid, "project_id": pid, "title": title,
            "assignee_id": mids[midx], "priority": pri, "status": status,
            "issue_type": itype, "story_points": sp, "estimated_hours": est,
            "actual_hours": act, "tags": tags, "blocker_note": blk,
        }).execute()
        client.table("activity_log").insert({
            "project_id": pid, "sprint_id": asid, "task_title": title,
            "actor": actor_names[midx], "action": "created",
            "field_changed": "status", "new_value": "Todo",
        }).execute()
