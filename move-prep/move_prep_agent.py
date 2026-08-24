#!/usr/bin/env python3
"""
USA Move Prep Agent for Manuel Lopes (@manueloslopes)
Reads checklist.json and generates a smart daily briefing using Claude.
Usage: python move_prep_agent.py
"""

import json
import os
import sys
from datetime import date
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)
except ImportError:
    print("WARNING: python-dotenv not installed.", file=sys.stderr)

import anthropic

CHECKLIST_PATH = Path(__file__).parent / "checklist.json"
MOVE_DATE = date(2026, 9, 22)
TODAY = date.today()

CATEGORY_LABELS = {
    "documents_visa": "Documents & Visa",
    "flights": "Flights",
    "accommodation": "Accommodation",
    "finances": "Finances",
    "phone_connectivity": "Phone & Connectivity",
    "health_insurance": "Health & Insurance",
    "content_creation": "Content Creation",
    "packing": "Packing",
    "admin_logistics": "Admin & Logistics",
}

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def load_checklist() -> dict:
    with open(CHECKLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def days_until(deadline_str: str) -> int:
    return (date.fromisoformat(deadline_str) - TODAY).days


def classify_task(task: dict) -> str:
    if task["done"]:
        return "done"
    days = days_until(task["deadline"])
    if days < 0:
        return "overdue"
    elif days == 0:
        return "due_today"
    elif days <= 7:
        return "due_this_week"
    elif days <= 14:
        return "due_in_two_weeks"
    else:
        return "upcoming"


def build_context_summary(data: dict) -> str:
    tasks = data["tasks"]
    meta = data["meta"]
    days_to_move = (MOVE_DATE - TODAY).days

    lines = []
    lines.append(f"=== MOVE PREP STATUS: {TODAY.isoformat()} ===")
    lines.append(f"Owner: {meta['owner']}")
    lines.append(f"Move date: {meta['move_date']} ({days_to_move} days away)")
    lines.append(f"Destination: {meta['destination']}")
    lines.append("")

    total = len(tasks)
    done = sum(1 for t in tasks if t["done"])
    overdue = [t for t in tasks if classify_task(t) == "overdue"]
    due_today = [t for t in tasks if classify_task(t) == "due_today"]
    due_week = [t for t in tasks if classify_task(t) == "due_this_week"]
    critical_pending = [t for t in tasks if not t["done"] and t["priority"] == "critical"]

    lines.append(f"PROGRESS: {done}/{total} tasks complete ({total - done} pending)")
    lines.append(f"Overdue: {len(overdue)} | Due today: {len(due_today)} | Due this week: {len(due_week)}")
    lines.append(f"Critical tasks still pending: {len(critical_pending)}")
    lines.append("")

    if overdue:
        lines.append("--- OVERDUE (IMMEDIATE ACTION REQUIRED) ---")
        for t in sorted(overdue, key=lambda x: PRIORITY_ORDER.get(x["priority"], 9)):
            days_over = abs(days_until(t["deadline"]))
            cat = CATEGORY_LABELS.get(t["category"], t["category"])
            lines.append(f"  [{t['priority'].upper()}] [{cat}] {t['title']}")
            lines.append(f"    Deadline was: {t['deadline']} ({days_over} days ago)")
            if t.get("notes"):
                lines.append(f"    Notes: {t['notes']}")
        lines.append("")

    if due_today:
        lines.append("--- DUE TODAY ---")
        for t in sorted(due_today, key=lambda x: PRIORITY_ORDER.get(x["priority"], 9)):
            cat = CATEGORY_LABELS.get(t["category"], t["category"])
            lines.append(f"  [{t['priority'].upper()}] [{cat}] {t['title']}")
            if t.get("notes"):
                lines.append(f"    Notes: {t['notes']}")
        lines.append("")

    if due_week:
        lines.append("--- DUE THIS WEEK ---")
        for t in sorted(due_week, key=lambda x: (days_until(x["deadline"]), PRIORITY_ORDER.get(x["priority"], 9))):
            cat = CATEGORY_LABELS.get(t["category"], t["category"])
            days_left = days_until(t["deadline"])
            lines.append(f"  [{t['priority'].upper()}] [{cat}] {t['title']} (in {days_left}d, by {t['deadline']})")
            if t.get("notes"):
                lines.append(f"    Notes: {t['notes']}")
        lines.append("")

    critical_upcoming = [
        t for t in tasks
        if not t["done"] and t["priority"] == "critical"
        and classify_task(t) not in ("overdue", "due_today", "due_this_week")
    ]
    if critical_upcoming:
        lines.append("--- UPCOMING CRITICAL TASKS ---")
        for t in sorted(critical_upcoming, key=lambda x: x["deadline"]):
            cat = CATEGORY_LABELS.get(t["category"], t["category"])
            days_left = days_until(t["deadline"])
            lines.append(f"  [CRITICAL] [{cat}] {t['title']} (in {days_left}d, by {t['deadline']})")
        lines.append("")

    lines.append("--- CATEGORY SUMMARY (pending tasks) ---")
    by_category: dict[str, list] = {}
    for t in tasks:
        if not t["done"]:
            by_category.setdefault(t["category"], []).append(t)
    for cat_key, cat_tasks in sorted(by_category.items()):
        cat_label = CATEGORY_LABELS.get(cat_key, cat_key)
        urgent = sum(1 for t in cat_tasks if classify_task(t) in ("overdue", "due_today", "due_this_week"))
        lines.append(f"  {cat_label}: {len(cat_tasks)} pending ({urgent} urgent)")
    lines.append("")

    return "\n".join(lines)


def generate_briefing(context: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set. Check your .env file.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = (
        "You are a sharp, friendly personal assistant helping Manuel Lopes (@manueloslopes), "
        "a Portuguese travel and outdoor content creator, prepare for his big move from Lisbon to Kauai, Hawaii, USA. "
        "He is moving on September 22, 2026 on a J-1 visa. Today is " + TODAY.isoformat() + ". "
        "Your job is to produce a concise, motivating, and actionable daily move-prep briefing. "
        "Be specific, direct, and practical. Prioritize ruthlessly. "
        "Use clear sections and plain text (no markdown). "
        "End with one specific TODAY'S TOP PRIORITY action item."
    )

    user_prompt = (
        "Here is today's move prep status:\n\n"
        + context
        + "\n\nGenerate today's move prep daily briefing for Manuel. "
        "Cover: (1) What needs immediate attention today, (2) What's coming up this week, "
        "(3) Any dangerous gaps or risks he might be overlooking, "
        "(4) One motivational note about the move, "
        "(5) TODAY'S TOP PRIORITY (single action item)."
    )

    print("Generating briefing with Claude...\n", file=sys.stderr)

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        thinking={"type": "adaptive"},
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return "\n".join(block.text for block in response.content if block.type == "text")


def main():
    print(f"USA Move Prep Agent — Daily Briefing", flush=True)
    print(f"Date: {TODAY.isoformat()}", flush=True)
    print(f"Days until move: {(MOVE_DATE - TODAY).days}", flush=True)
    print("=" * 60, flush=True)

    data = load_checklist()
    context = build_context_summary(data)

    print(context)
    print("=" * 60)
    print("CLAUDE AI BRIEFING")
    print("=" * 60)
    print(generate_briefing(context))


if __name__ == "__main__":
    main()
