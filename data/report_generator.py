from io import BytesIO

from reportlab.platypus import (
SimpleDocTemplate,
Paragraph,
Spacer,
PageBreak,
Table,
TableStyle
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

def make_table(data):


    table = Table(data)

    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ])
    )

    return table


def generate_member_report(
member_name,
role,
project_name,
tasks,
updates,
sprint_lookup
):


    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    story = []

    # =====================================================
    # CALCULATIONS
    # =====================================================

    total_tasks = len(tasks)

    completed_tasks = sum(
        1 for t in tasks
        if t.get("status") == "Done"
    )

    completion_rate = (
        round(
            completed_tasks / total_tasks * 100,
            1
        )
        if total_tasks
        else 0
    )

    story_points = sum(
        int(t.get("story_points") or 0)
        for t in tasks
    )

    actual_hours = sum(
        float(t.get("actual_hours") or 0)
        for t in tasks
    )

    estimated_hours = sum(
        float(t.get("estimated_hours") or 0)
        for t in tasks
    )

    efficiency = (
        round(
            (estimated_hours / actual_hours) * 100,
            1
        )
        if actual_hours > 0
        else 100
    )

    # =====================================================
    # PAGE 1
    # =====================================================

    story.append(
        Paragraph(
            "AI Sprint Manager",
            styles["Title"]
        )
    )

    story.append(
        Paragraph(
            "Member Performance Report",
            styles["Heading1"]
        )
    )

    story.append(Spacer(1, 20))

    story.append(
        Paragraph(
            f"<b>Member Name:</b> {member_name}",
            styles["BodyText"]
        )
    )

    story.append(
        Paragraph(
            f"<b>Role:</b> {role}",
            styles["BodyText"]
        )
    )

    story.append(
        Paragraph(
            f"<b>Project:</b> {project_name}",
            styles["BodyText"]
        )
    )

    story.append(PageBreak())

    # =====================================================
    # PAGE 2
    # EXECUTIVE SUMMARY
    # =====================================================

    story.append(
        Paragraph(
            "Executive Summary",
            styles["Heading1"]
        )
    )

    summary_data = [
        ["Metric", "Value"],
        ["Tasks Assigned", str(total_tasks)],
        ["Tasks Completed", str(completed_tasks)],
        ["Completion Rate", f"{completion_rate}%"],
        ["Story Points", str(story_points)],
        ["Estimated Hours", str(estimated_hours)],
        ["Actual Hours", str(actual_hours)],
        ["Time Efficiency", f"{efficiency}%"],
        ["Daily Updates", str(len(updates))]
    ]

    story.append(
        make_table(summary_data)
    )

    story.append(PageBreak())

    # =====================================================
    # PAGE 3
    # SPRINT PERFORMANCE
    # =====================================================

    story.append(
        Paragraph(
            "Sprint-wise Performance",
            styles["Heading1"]
        )
    )

    sprint_stats = {}

    for t in tasks:

        sprint_name = sprint_lookup.get(
            t.get("sprint_id"),
            "Unknown Sprint"
        )

        if sprint_name not in sprint_stats:

            sprint_stats[sprint_name] = {
                "assigned": 0,
                "done": 0,
                "points": 0
            }

        sprint_stats[sprint_name]["assigned"] += 1

        if t.get("status") == "Done":
            sprint_stats[sprint_name]["done"] += 1

        sprint_stats[sprint_name]["points"] += (
            t.get("story_points") or 0
        )

    sprint_rows = [
        [
            "Sprint",
            "Assigned",
            "Completed",
            "Story Points"
        ]
    ]

    for sprint_name, data in sprint_stats.items():

        sprint_rows.append([
            sprint_name,
            str(data["assigned"]),
            str(data["done"]),
            str(data["points"])
        ])

    story.append(
        make_table(sprint_rows)
    )

    story.append(PageBreak())

    story.append(
        Paragraph(
            "Report Generated Successfully",
            styles["Heading2"]
        )
    )
    print("REACHED END OF REPORT FUNCTION")
    doc.build(story)

    pdf = buffer.getvalue()
    print("PDF SIZE =", len(pdf))
    buffer.close()

    return pdf
    