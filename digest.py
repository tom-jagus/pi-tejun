"""Digest-specific validation and recoverable, no-overwrite coverage publication."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re

TOPICS = ("ai", "security", "linux", "developer-tools", "hardware", "github",
          "homelab", "poland")


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("coverage timestamp must be a string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("coverage timestamps require a timezone")
    return result


def read_record(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"missing or symlinked history: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"invalid history object: {path}")
    return value


def inventory(workspace, now=None):
    """Read only finalized pairs. Orphans require explicit operator recovery."""
    workspace = Path(workspace)
    for name in ("reports", "history"):
        if (workspace / name).is_symlink():
            raise ValueError(f"digest {name} must not be a symlink")
    records = []
    for path in sorted((workspace / "history").glob("digest-*.json")):
        if path.name.endswith(".partial.json"):
            continue
        record = read_record(path)
        report = workspace / "reports" / (path.stem + ".md")
        if report.is_symlink() or not report.is_file():
            raise ValueError(f"history without report; inspect {path}")
        if record.get("sha256") != hashlib.sha256(report.read_bytes()).hexdigest():
            raise ValueError(f"report/history mismatch; inspect {path}")
        validate_record(record)
        records.append(record)
    for report in (workspace / "reports").glob("digest-*.md"):
        if not report.name.endswith(".partial.md") and not (
                workspace / "history" / (report.stem + ".json")).is_file():
            raise ValueError(f"report without history; inspect {report} before retrying")
    now = now or datetime.now(timezone.utc)
    end = now.isoformat()
    start = max((timestamp(r["end"]) for r in records), default=now - timedelta(hours=24))
    if start > now:
        raise ValueError("digest history is ahead of the current clock")
    return {"start": start.isoformat(), "end": end, "previous": records,
            "topics": list(TOPICS)}


def validate_record(record):
    if not isinstance(record, dict) or record.get("version") != 1:
        raise ValueError("digest history requires version 1")
    if timestamp(record.get("start")) >= timestamp(record.get("end")):
        raise ValueError("invalid coverage interval")
    coverage = record.get("coverage")
    if not isinstance(coverage, list) or not coverage:
        raise ValueError("history needs explicit coverage entries")
    for entry in coverage:
        if not isinstance(entry, dict) or not all(isinstance(entry.get(k), str) for k in (
                "subject", "start", "end", "status", "reason")):
            raise ValueError("invalid coverage entry")
        if (not entry["subject"] or entry["status"] not in {"checked", "failed"}
                or timestamp(entry["start"]) >= timestamp(entry["end"])):
            raise ValueError("invalid coverage subject, status, or interval")
        if entry["status"] == "failed" and not entry["reason"].strip():
            raise ValueError("failed coverage needs a reason")
    findings = record.get("findings")
    if not isinstance(findings, list):
        raise ValueError("history needs a findings list, possibly empty")
    for finding in findings:
        if not isinstance(finding, dict) or not all(isinstance(finding.get(k), str)
                and finding[k].strip() for k in ("subject", "summary", "date", "change")):
            raise ValueError("invalid retained finding")
        urls = finding.get("sources")
        if not isinstance(urls, list) or not urls or not all(
                isinstance(url, str) and re.fullmatch(r"https?://[^\s]+", url) for url in urls):
            raise ValueError("findings require source URLs")


def validate(report, record, context):
    validate_record(record)
    if any(record[key] != context[key] for key in ("start", "end")):
        raise ValueError("history does not match the reserved research period")
    required = {(topic, context["start"], context["end"]) for topic in TOPICS}
    required.update(("watch:" + entry, context["start"], context["end"])
                    for entry in context.get("watchlist", []))
    outcomes = {}
    for previous in sorted(context["previous"], key=lambda item: timestamp(item["end"])):
        for entry in previous["coverage"]:
            outcomes[(entry["subject"], entry["start"], entry["end"])] = entry["status"]
    active_watch = {"watch:" + entry for entry in context.get("watchlist", [])}
    required.update(key for key, status in outcomes.items() if status == "failed"
                    and (not key[0].startswith("watch:") or key[0] in active_watch))
    actual = [(e["subject"], e["start"], e["end"]) for e in record["coverage"]]
    if len(actual) != len(set(actual)) or not required.issubset(actual):
        raise ValueError("coverage is missing a topic or gap retry, or contains duplicates")
    title = report.partition("\n")[0]
    if (not re.fullmatch(r"# Digest - \d{4}-\d{2}-\d{2}", title)
            or not report.endswith("\n") or "\x00" in report or "\r" in report):
        raise ValueError("digest needs an ISO-dated title and final newline")
    datetime.strptime(title.removeprefix("# Digest - "), "%Y-%m-%d")
    if f"Coverage: {context['start']} to {context['end']}" not in report:
        raise ValueError("digest must state its checked period")
    prior_urls = {url for previous in context["previous"]
                  for finding in previous["findings"] for url in finding["sources"]}
    if any(finding["change"].strip().casefold() == "new"
           and prior_urls.intersection(finding["sources"]) for finding in record["findings"]):
        raise ValueError("previously covered sources need an explicit material change")
    if record["findings"]:
        if "## Findings\n" not in report:
            raise ValueError("missing findings section")
        for finding in record["findings"]:
            if not all(url in report for url in finding["sources"]):
                raise ValueError("report is missing retained source URLs")
    elif "No verified updates since the last check." not in report:
        raise ValueError("empty findings must be explicit")
    if "## Research failures" in report:
        raise ValueError("keep detailed research failures in coverage history")
    incomplete = any(e["status"] == "failed" for e in record["coverage"])
    has_note = "Some checks remain incomplete" in report
    if incomplete and (not has_note or "These checks will be retried." not in report):
        raise ValueError("incomplete coverage needs a visible brief qualification and retry notice")
    if not incomplete and has_note:
        raise ValueError("incomplete-check note does not match coverage history")
    record = dict(record)
    record["sha256"] = hashlib.sha256(report.encode("utf-8")).hexdigest()
    return record
