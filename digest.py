"""Bounded recent-report context for discovery, without coverage bookkeeping."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

TOPICS = ("ai", "security", "linux", "developer-tools", "hardware", "github",
          "homelab", "poland")
RECENT_REPORTS = 3
REPORT_CONTEXT_CHARS = 6000
MAX_LOOKBACK = timedelta(days=7)


def recent_reports(workspace, workflow, now):
    """Read bounded excerpts of finalized reports, using runner-owned filenames.

    Ignore partials and old JSON history. Filename dates identify run start,
    avoiding mtime changes caused by editing or copying a report.
    """
    directory = Path(workspace) / "reports"
    if directory.is_symlink():
        raise ValueError("reports directory must not be a symlink")
    candidates = []
    pattern = re.compile(re.escape(workflow) + r"-(\d{8}T\d{6}Z)-[a-f0-9]{12}\.md")
    for path in directory.glob(f"{workflow}-*.md"):
        match = pattern.fullmatch(path.name)
        if not match or path.is_symlink() or not path.is_file():
            continue
        started = datetime.strptime(match[1], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        if started > now:
            raise ValueError(f"report timestamp is ahead of the current clock: {path}")
        candidates.append((started, path))
    result = []
    for started, path in sorted(candidates, reverse=True)[:RECENT_REPORTS]:
        with path.open(encoding="utf-8") as stream:
            text = stream.read(REPORT_CONTEXT_CHARS + 1)
        result.append({"path": str(path), "started_at": started.isoformat(),
                       "excerpt": text[:REPORT_CONTEXT_CHARS],
                       "truncated": len(text) > REPORT_CONTEXT_CHARS})
    return result


def inventory(workspace, now=None):
    now = now or datetime.now(timezone.utc)
    recent = recent_reports(workspace, "digest", now)
    previous = datetime.fromisoformat(recent[0]["started_at"]) if recent else None
    start = max(previous, now - MAX_LOOKBACK) if previous else now - timedelta(hours=24)
    # Run filenames have second precision. A repeat within that second still
    # needs a nonempty research window.
    if start >= now:
        start = now - timedelta(seconds=1)
    return {"start": start.isoformat(), "end": now.isoformat(),
            "topics": list(TOPICS), "recent_reports": recent,
            "lookback_capped": previous is not None and previous < now - MAX_LOOKBACK}


def validate(report, context):
    """Check basic report integrity, not research quality or completeness."""
    if not report.strip() or "\x00" in report:
        raise ValueError("report must be nonempty text")
    if f"Coverage: {context['start']} to {context['end']}" not in report:
        raise ValueError("digest must state its research period")
