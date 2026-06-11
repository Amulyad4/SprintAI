from data.supabase_client import get_client


def create_daily_update(
    project_id,
    member_id,
    work_done,
    blockers,
    tomorrow_plan,
    hours_worked
):
    return (
        get_client(require_auth=True)
        .table("daily_updates")
        .insert({
            "project_id": int(project_id),
            "member_id": int(member_id),
            "work_done": work_done,
            "blockers": blockers,
            "tomorrow_plan": tomorrow_plan,
            "hours_worked": float(hours_worked)
        })
        .execute()
    )


def load_daily_updates(project_id):
    return (
        get_client(require_auth=True)
        .table("daily_updates")
        .select("*")
        .eq("project_id", int(project_id))
        .order("created_at", desc=True)
        .execute()
    )