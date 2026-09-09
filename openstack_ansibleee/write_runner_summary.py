#!/usr/bin/env python3
#
# Copyright 2026 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Summarize ansible-runner artifacts for the pod termination log and stdout."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _latest_run_dir(artifacts_root: Path) -> Path | None:
    if not artifacts_root.exists():
        return None

    candidates = [path for path in artifacts_root.iterdir() if path.is_dir()]
    if not candidates:
        return None

    return max(candidates, key=lambda path: path.stat().st_mtime)


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _latest_stats_event(job_events_dir: Path) -> dict[str, Any]:
    if not job_events_dir.exists():
        return {}

    for event_file in job_events_dir.glob("*.json"):
        try:
            event = _load_json(event_file)
        except (json.JSONDecodeError, OSError, TypeError, UnicodeDecodeError):
            continue
        if not isinstance(event, dict):
            continue
        if event.get("event") != "playbook_on_stats":
            continue

        return event

    return {}


def _load_status(run_dir: Path) -> dict[str, Any]:
    """Read the run verdict from ansible-runner artifacts.

    ansible-runner writes ``status`` (e.g. ``successful``, ``failed``,
    ``timeout``) and ``rc`` as plain-text files.
    """
    try:
        status = (run_dir / "status").read_text(encoding="utf-8").strip() or None
    except (OSError, UnicodeDecodeError):
        status = None

    try:
        rc = int((run_dir / "rc").read_text(encoding="utf-8").strip())
    except (OSError, ValueError, UnicodeDecodeError):
        rc = None

    return {"status": status, "rc": rc}


def _last_event(job_events_dir: Path) -> dict[str, Any]:
    last: dict[str, Any] = {}
    if not job_events_dir.exists():
        return last
    for event_file in job_events_dir.glob("*.json"):
        try:
            event = _load_json(event_file)
        except (OSError, json.JSONDecodeError, TypeError, UnicodeDecodeError):
            continue
        if not isinstance(event, dict):
            continue
        counter = event.get("counter", 0)
        if isinstance(counter, bool) or not isinstance(counter, (int, float)):
            continue
        if counter >= last.get("counter", 0):
            last = event
    return last


def _host_keys(stats_dict: Any) -> set[str]:
    if not isinstance(stats_dict, dict):
        return set()

    return {str(host) for host in stats_dict.keys()}


def build_summary(run_dir: Path) -> dict[str, Any]:
    stats_event = _latest_stats_event(run_dir / "job_events")
    event_data = _as_dict(stats_event.get("event_data"))

    total_hosts = _host_keys(event_data.get("processed"))
    failure_hosts = _host_keys(event_data.get("failures"))
    unreachable_hosts = _host_keys(event_data.get("dark"))
    impacted_hosts = failure_hosts | unreachable_hosts

    total_count = len(total_hosts)
    failed_count = len(failure_hosts)
    unreachable_count = len(unreachable_hosts)
    impacted_count = len(impacted_hosts)

    failure_pct = 0
    if total_count:
        failure_pct = ((impacted_count * 100) + (total_count // 2)) // total_count

    summary = {
        "failedHostList": sorted(failure_hosts),
        "totalHosts": total_count,
        "failedHosts": failed_count,
        "unreachableHosts": unreachable_count,
        "unreachableHostList": sorted(unreachable_hosts),
        "failurePercent": failure_pct,
    }

    return summary


def _write_summary(summary: dict[str, Any], output_path: Path) -> None:
    payload = json.dumps(summary, separators=(",", ":"), sort_keys=True)
    output_path.write_text(payload, encoding="utf-8")


def main() -> int:
    artifacts_root = Path(
        os.environ.get("EDPM_AEE_ARTIFACTS_ROOT", "/runner/artifacts")
    )
    output_path = Path(
        os.environ.get("EDPM_AEE_TERMINATION_LOG", "/dev/termination-log")
    )

    run_dir = _latest_run_dir(artifacts_root)
    if run_dir is None:
        return 0

    summary = build_summary(run_dir)
    _write_summary(summary, output_path)

    status = _load_status(run_dir)
    if status.get("status") == "successful":
        return 0

    event_data = _as_dict(_last_event(run_dir / "job_events").get("event_data"))
    task = event_data.get("task")
    rc = status.get("rc")
    print(
        "EDPM AEE SUMMARY: "
        f"status={status.get('status') or '-'} "
        f"rc={rc if rc is not None else '-'} "
        f"total_hosts={summary['totalHosts']} "
        f"failed_hosts={summary['failedHosts']} "
        f"unreachable_hosts={summary['unreachableHosts']} "
        f"last_task={task.get('name') if isinstance(task, dict) else '-'} "
        f"last_host={event_data.get('host') or '-'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
