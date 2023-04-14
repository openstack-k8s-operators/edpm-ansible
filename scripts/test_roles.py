#!/usr/bin/env python

import glob
import subprocess as sp
import os.path

SKIP_LIST = [
    "edpm_ovn"
]


def _test_passed(result):
    if 'CRITICAL' in result['stdout'] or result['stderr'] or result['process'].return_code != 0:
        return False
    return True


def main():
    role_paths = glob.glob("./roles/*")
    print(f"Found roles: {role_paths}")
    results = {}

    for role in role_paths:

        role_name = os.path.basename(role)
        if role_name in SKIP_LIST:
            continue
        print(f"Testing {role_name} ...")
        try:
            process = sp.Popen(
                "PY_COLORS=0 molecule test --all",
                cwd=role, shell=True, stdout=sp.PIPE, stderr=sp.PIPE, text=True)
            outputs = process.communicate()
            results[role_name] = {
                'stdout': outputs[0], 'stderr': outputs[1], 'process': process}
            results[role_name]['passed'] = _test_passed(results[role_name])
        except Exception as ex:
            results[role_name] = {'outputs': ("", "ERROR"), 'process': ex, 'passed': False}

    print("*" * 80)

    for role, test_result in results.items():

        print(f"{role} - Passed: {test_result['passed']}")
        if not test_result['passed']:
            print(f"STDOUT: {test_result['stdout']}\nSTDERR: {test_result['stderr']}")
        print("-" * 80)

    print("Final report")
    print("+" * 12)
    for role, test_result in results.items():
        print(f"{role} - Passed: {results[role_name]['passed']}")
    print("-" * 80)


if __name__ == '__main__':
    main()
