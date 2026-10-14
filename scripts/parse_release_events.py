import json
from datetime import datetime
from pathlib import Path


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# Read the fake events.
events = [
    json.loads(path.read_text())
    for path in sorted(Path("test-data").glob("*.txt"))
]

if not events:
    raise ValueError("No event files found in test-data")

# Find release branches being created.
for event in events:
    payload = event["payload"]

    if event["metadata"]["event_type"] != "create":
        continue

    if payload["ref_type"] != "branch":
        continue

    branch = payload["ref"]

    if not branch.startswith("release/"):
        continue

    repository = payload["repository"]["full_name"]
    started = parse_time(event["metadata"]["received_at"])

    print(f"\nRepository: {repository}")
    print(f"Release: {branch}")
    print(f"Branch created: {started.isoformat()}")

    # Collect merged PRs for this repository.
    merged_prs = [
        item["payload"]["pull_request"]
        for item in events
        if item["metadata"]["event_type"] == "pull_request"
        and item["payload"]["repository"]["full_name"] == repository
        and item["payload"]["action"] == "closed"
        and item["payload"]["pull_request"]["merged"] is True
    ]

    # Find the release branch merging into main.
    release_pr = next(
        (
            pr for pr in merged_prs
            if pr["head"]["ref"] == branch
            and pr["base"]["ref"] == "main"
        ),
        None,
    )

    if release_pr is None:
        print("Waiting for release to merge into main")
        continue

    released = parse_time(release_pr["merged_at"])

    print(f"Merged into main: {released.isoformat()}")
    print(f"Release preparation: {released - started}")

    # Find main merging back into develop.
    sync_pr = next(
        (
            pr for pr in merged_prs
            if pr["head"]["ref"] == "main"
            and pr["base"]["ref"] == "develop"
            and pr["head"]["sha"] == release_pr["merge_commit_sha"]
        ),
        None,
    )

    if sync_pr is None:
        print("No matching merge back into develop found")
        continue

    synced = parse_time(sync_pr["merged_at"])

    print(f"Merged back into develop: {synced.isoformat()}")
    print(f"Merge-back delay: {synced - released}")