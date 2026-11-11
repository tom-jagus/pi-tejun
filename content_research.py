"""User decisions and recent-report context for content research."""
from calendar import monthrange
from datetime import datetime, timedelta
import json
from pathlib import Path
import re

import digest

AREAS = ("ai-agents", "developer-tools", "linux-open-source",
         "software-design", "self-hosting-infrastructure")


def decisions(workspace):
    """Read user-owned lists, rejecting duplicate or conflicting identities."""
    result, seen = {}, set()
    for name in ("pursue", "reject"):
        path = Path(workspace) / f"{name}.json"
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing or symlinked decision input: {path}")
        values = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(values, list):
            raise ValueError(f"{name}.json must be a JSON list")
        for item in values:
            if not isinstance(item, dict) or not all(
                    isinstance(item.get(k), str) and item[k].strip() for k in ("id", "subject")):
                raise ValueError(f"{name}.json entries need nonempty id and subject")
            urls = item.get("sources", [])
            if (not isinstance(urls, list) or any(not isinstance(u, str) or not
                    re.fullmatch(r"https?://[^\s]+", u) for u in urls)
                    or not isinstance(item.get("reason", ""), str)):
                raise ValueError(f"invalid sources or reason in {name}.json")
            keys = {"id:" + item["id"].casefold(), "name:" + item["subject"].casefold(),
                    *("url:" + url for url in urls)}
            if seen & keys:
                raise ValueError("duplicate or conflicting pursue/reject decisions; inspect both lists")
            seen.update(keys)
        result[name] = values
    return result


def inventory(workspace, window, now=None):
    now = now or datetime.now().astimezone()
    if window == "three-months":
        month = (now.year * 12 + now.month - 1) - 3
        year, month = divmod(month, 12)
        month += 1
        start = now.replace(year=year, month=month, day=min(now.day, monthrange(year, month)[1]))
    elif window == "four-weeks":
        start = now - timedelta(weeks=4)
    else:
        raise ValueError("research_window must be three-months or four-weeks")
    sunday = now.date() - timedelta(days=(now.weekday() + 1) % 7)
    return {"start": start.isoformat(), "end": now.isoformat(),
            "week_start": sunday.isoformat(), "week_end": (sunday + timedelta(days=6)).isoformat(),
            "decisions": decisions(workspace), "areas": list(AREAS),
            "recent_reports": digest.recent_reports(workspace, "content-research", now)}


def validate(report, context, workspace):
    """Check basic integrity and changed decisions, not editorial judgment."""
    if not report.strip() or "\x00" in report:
        raise ValueError("report must be nonempty text")
    if decisions(workspace) != context["decisions"]:
        raise ValueError("decision inputs changed during the run; inspect the partial before retrying")
