"""Turn webhook payloads into short human-readable messages (English, bot-style)."""


def format_event(source: str, event_type: str, payload: dict) -> str:
    if source == "github":
        return _format_github(event_type, payload)
    title = payload.get("title") or payload.get("message") or ""
    suffix = f": {title}" if title else ""
    return f"[{source}] {event_type or 'event'}{suffix}"


def _format_github(event_type: str, p: dict) -> str:
    repo = (p.get("repository") or {}).get("full_name", "unknown-repo")
    sender = (p.get("sender") or {}).get("login", "someone")

    if event_type == "ping":
        return f"[github] Webhook connected for {repo} (ping OK)"
    if event_type == "push":
        branch = (p.get("ref") or "").replace("refs/heads/", "")
        commits = p.get("commits") or []
        n = len(commits)
        first = commits[0]["message"].splitlines()[0] if commits else ""
        line = f"[github] Push to {repo}:{branch} by {sender} - {n} commit(s)"
        return f"{line}\n{first}" if first else line
    if event_type == "pull_request":
        pr = p.get("pull_request") or {}
        return (f"[github] PR #{pr.get('number')} {p.get('action')} in {repo} by {sender}"
                f"\n{pr.get('title', '')}")
    if event_type == "issues":
        issue = p.get("issue") or {}
        return (f"[github] Issue #{issue.get('number')} {p.get('action')} in {repo} by {sender}"
                f"\n{issue.get('title', '')}")
    if event_type == "star":
        return f"[github] {repo} {p.get('action', 'starred')} by {sender}"
    return f"[github] {event_type or 'event'} on {repo} by {sender}"
