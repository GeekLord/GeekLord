#!/usr/bin/env python3
"""
Refresh the data that powers the profile graphics.

Writes:
  data/profile-stats.json            account + 12-month contribution totals
  data/contribution-calendar.json    53 week x 7 day grid with real per-day counts
  data/languages.json                language mix, by repo count and by bytes
  data/activity-hours.json           recent public activity by hour (IST)

Only the Python standard library is used, so CI needs no dependencies. The token
is read from GITHUB_TOKEN / GH_TOKEN, falling back to `gh auth token` locally.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LOGIN = os.environ.get("PROFILE_LOGIN", "GeekLord")
IST = timezone(timedelta(hours=5, minutes=30))
API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"
LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

QUERY = """
query ($login: String!) {
  user(login: $login) {
    login
    name
    bio
    location
    websiteUrl
    createdAt
    followers { totalCount }
    following { totalCount }
    ownRepos: repositories(ownerAffiliations: OWNER, isFork: false) { totalCount }
    allRepos: repositories(ownerAffiliations: OWNER) { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        name
        url
        description
        stargazerCount
        pushedAt
        primaryLanguage { name }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
      restrictedContributionsCount
      contributionYears
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount contributionLevel }
        }
      }
    }
  }
}
"""


def token() -> str:
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(name):
            return os.environ[name]
    try:
        return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit("No token found. Set GITHUB_TOKEN or authenticate the gh CLI.")


def graphql(query: str, variables: dict) -> dict:
    payload = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request(
        GRAPHQL, data=payload,
        headers={"Authorization": f"bearer {token()}", "Content-Type": "application/json",
                 "User-Agent": "geeklord-profile-readme"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        body = json.loads(response.read())
    if "errors" in body:
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]


def rest(path: str) -> list | dict:
    request = urllib.request.Request(
        f"{API}{path}",
        headers={"Authorization": f"bearer {token()}", "Accept": "application/vnd.github+json",
                 "User-Agent": "geeklord-profile-readme"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read())


def build_calendar(collection: dict) -> dict:
    calendar = collection["contributionCalendar"]
    weeks = []
    for week in calendar["weeks"]:
        days = []
        for day in week["contributionDays"]:
            days.append({
                "date": day["date"],
                "count": day["contributionCount"],
                "level": LEVELS.get(day["contributionLevel"], 0),
            })
        weeks.append(days)
    return {
        "total": calendar["totalContributions"],
        "weeks": weeks,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def build_languages(nodes: list[dict]) -> dict:
    by_repo = Counter()
    by_bytes = Counter()
    unnamed = 0
    for node in nodes:
        primary = (node.get("primaryLanguage") or {}).get("name")
        if primary:
            by_repo[primary] += 1
        else:
            unnamed += 1
        for edge in (node.get("languages") or {}).get("edges", []):
            by_bytes[edge["node"]["name"]] += edge["size"]

    owned = sum(by_repo.values())
    entries = []
    for name, repos in by_repo.most_common():
        entries.append({
            "name": name,
            "repos": repos,
            "share": round(repos / max(owned, 1) * 100, 2),
            "detail": f"{repos} repo{'s' if repos != 1 else ''}",
            "bytes": by_bytes.get(name, 0),
        })
    if unnamed:
        entries.append({"name": "Docs / config", "repos": unnamed,
                        "share": round(unnamed / max(owned + unnamed, 1) * 100, 2),
                        "detail": f"{unnamed} repos", "bytes": 0})
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "basis": "own non-fork repositories, counted by primary language",
        "by_repo": entries,
        "by_bytes": [{"name": name, "bytes": size} for name, size in by_bytes.most_common()],
    }


def build_hours() -> dict:
    hours = Counter()
    events = 0
    for page in range(1, 4):
        try:
            batch = rest(f"/users/{LOGIN}/events/public?per_page=100&page={page}")
        except urllib.error.HTTPError as error:
            print(f"  events page {page} unavailable ({error.code})")
            break
        if not batch:
            break
        for event in batch:
            stamp = event.get("created_at")
            if not stamp:
                continue
            moment = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(IST)
            hours[moment.hour] += 1
            events += 1
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "timezone": "Asia/Kolkata (IST)",
        "sample": events,
        "hours": [{"hour": hour, "events": hours.get(hour, 0)} for hour in range(24)],
    }


def main() -> None:
    DATA.mkdir(exist_ok=True)
    data = graphql(QUERY, {"login": LOGIN})["user"]
    collection = data["contributionsCollection"]

    created = datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00"))
    stars = sum(node["stargazerCount"] for node in data["repositories"]["nodes"])
    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "login": data["login"],
        "name": data["name"],
        "bio": data["bio"],
        "location": data["location"],
        "website": data["websiteUrl"],
        "joined": data["createdAt"][:10],
        "joined_year": created.year,
        "years_on_github": datetime.now(timezone.utc).year - created.year,
        "followers": data["followers"]["totalCount"],
        "following": data["following"]["totalCount"],
        "own_repos": data["ownRepos"]["totalCount"],
        "public_repos": data["allRepos"]["totalCount"],
        "stars": stars,
        "contributions": collection["contributionCalendar"]["totalContributions"],
        "commits": collection["totalCommitContributions"],
        "pull_requests": collection["totalPullRequestContributions"],
        "issues": collection["totalIssueContributions"],
        "private_contributions": collection["restrictedContributionsCount"],
        "contribution_years": sorted(collection["contributionYears"]),
    }

    calendars = {
        "profile-stats.json": stats,
        "contribution-calendar.json": build_calendar(collection),
        "languages.json": build_languages(data["repositories"]["nodes"]),
        "activity-hours.json": build_hours(),
    }
    for name, payload in calendars.items():
        path = DATA / name
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.1f} KB)")

    print(f"\n{stats['name']} · {stats['contributions']} contributions · "
          f"{stats['own_repos']} own repos · {stats['followers']} followers")


if __name__ == "__main__":
    main()
