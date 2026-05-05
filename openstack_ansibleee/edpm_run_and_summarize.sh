#!/usr/bin/env bash
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

set -u

write_runner_summary() {
    local summary_helper
    local runner_path
    local runner_python
    summary_helper="${EDPM_AEE_SUMMARY_HELPER:-/opt/builder/bin/write_runner_summary.py}"
    runner_path="$(command -v ansible-runner 2>/dev/null || true)"
    runner_python="$(sed -n '1s/^#!//p' "${runner_path}" 2>/dev/null || true)"

    if [ -n "${runner_python}" ] && [ -x "${runner_python}" ]; then
        "${runner_python}" "${summary_helper}" >/dev/null 2>&1 || true
    fi
}

if [ "$#" -eq 0 ]; then
    write_runner_summary
    exit 0
fi

"$@"
rc=$?

write_runner_summary

exit "${rc}"
