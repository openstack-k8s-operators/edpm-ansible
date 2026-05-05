# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os

from openstack_ansibleee import write_runner_summary


def _create_run_dir(tmp_path, run_name, counter, processed, failures, dark):
    run_dir = tmp_path / "artifacts" / run_name
    events_dir = run_dir / "job_events"
    events_dir.mkdir(parents=True)
    (run_dir / "rc").write_text("2", encoding="utf-8")
    (run_dir / "status").write_text("failed", encoding="utf-8")
    (events_dir / f"{counter}-stats.json").write_text(
        json.dumps(
            {
                "counter": counter,
                "event": "playbook_on_stats",
                "event_data": {
                    "processed": processed,
                    "failures": failures,
                    "dark": dark,
                },
            }
        ),
        encoding="utf-8",
    )
    return run_dir


def test_build_summary_includes_failure_percentage(tmp_path):
    run_dir = _create_run_dir(
        tmp_path,
        "run-one",
        10,
        {"host-a": 1, "host-b": 1, "host-c": 1},
        {"host-b": 1},
        {"host-c": 1},
    )

    summary = write_runner_summary.build_summary(run_dir)

    assert summary == {
        "failedHostList": ["host-b"],
        "failedHosts": 1,
        "failurePercent": 67,
        "totalHosts": 3,
        "unreachableHostList": ["host-c"],
        "unreachableHosts": 1,
    }


def test_latest_run_dir_uses_most_recent_artifacts(tmp_path):
    older_run = _create_run_dir(
        tmp_path, "older-run", 2, {"host-a": 1}, {"host-a": 1}, {}
    )
    newer_run = _create_run_dir(
        tmp_path, "newer-run", 3, {"host-a": 1, "host-b": 1}, {}, {}
    )

    os.utime(newer_run, None)
    selected_run = write_runner_summary._latest_run_dir(tmp_path / "artifacts")

    assert older_run != newer_run
    assert selected_run == newer_run


def test_latest_stats_event_skips_malformed_files(tmp_path):
    events_dir = tmp_path / "job_events"
    events_dir.mkdir()
    (events_dir / "bad-json.json").write_text("{not-json", encoding="utf-8")
    (events_dir / "not-stats.json").write_text(
        json.dumps(
            {
                "counter": 1,
                "event": "runner_on_ok",
                "event_data": {"processed": {"host-a": 1}},
            }
        ),
        encoding="utf-8",
    )
    (events_dir / "good.json").write_text(
        json.dumps(
            {
                "counter": 2,
                "event": "playbook_on_stats",
                "event_data": {"processed": {"host-b": 1}},
            }
        ),
        encoding="utf-8",
    )

    latest_event = write_runner_summary._latest_stats_event(events_dir)

    assert latest_event["counter"] == 2
    assert latest_event["event_data"]["processed"] == {"host-b": 1}


def test_host_keys_handles_unexpected_values():
    assert write_runner_summary._host_keys(None) == set()
    assert write_runner_summary._host_keys("not-a-dict") == set()
    assert write_runner_summary._host_keys({"host-a": 1, "host-b": 0}) == {
        "host-a",
        "host-b",
    }


def test_build_summary_handles_missing_job_events(tmp_path):
    run_dir = tmp_path / "artifacts" / "run-one"
    run_dir.mkdir(parents=True)

    summary = write_runner_summary.build_summary(run_dir)

    assert summary == {
        "failedHostList": [],
        "failedHosts": 0,
        "failurePercent": 0,
        "totalHosts": 0,
        "unreachableHostList": [],
        "unreachableHosts": 0,
    }


def test_build_summary_handles_zero_processed_hosts(tmp_path):
    run_dir = _create_run_dir(
        tmp_path,
        "run-zero",
        4,
        {},
        {"host-b": 1},
        {},
    )

    summary = write_runner_summary.build_summary(run_dir)

    assert summary == {
        "failedHostList": ["host-b"],
        "failedHosts": 1,
        "failurePercent": 0,
        "totalHosts": 0,
        "unreachableHostList": [],
        "unreachableHosts": 0,
    }


def test_main_writes_summary_to_requested_output(tmp_path, monkeypatch):
    _create_run_dir(
        tmp_path,
        "run-one",
        8,
        {"host-a": 1, "host-b": 1},
        {"host-b": 1},
        {},
    )
    output_path = tmp_path / "termination.log"

    monkeypatch.setenv("EDPM_AEE_ARTIFACTS_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("EDPM_AEE_TERMINATION_LOG", str(output_path))

    assert write_runner_summary.main() == 0

    written_summary = json.loads(output_path.read_text(encoding="utf-8"))
    assert written_summary["failedHostList"] == ["host-b"]
    assert written_summary["unreachableHostList"] == []
    assert written_summary["totalHosts"] == 2
    assert written_summary["failedHosts"] == 1
    assert written_summary["failurePercent"] == 50


def test_main_returns_zero_when_no_artifacts_exist(tmp_path, monkeypatch):
    output_path = tmp_path / "termination.log"

    monkeypatch.setenv("EDPM_AEE_ARTIFACTS_ROOT", str(tmp_path / "missing"))
    monkeypatch.setenv("EDPM_AEE_TERMINATION_LOG", str(output_path))

    assert write_runner_summary.main() == 0
    assert not output_path.exists()
