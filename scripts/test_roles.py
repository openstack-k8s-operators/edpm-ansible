#!/usr/bin/env python

import glob
import subprocess as sp
import os.path

SKIP_LIST = [
    "edpm_ovn"
]


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
            results[role_name] = {
                'outputs': process.communicate(), 'process': process}
        except Exception as ex:
            results[role_name] = {'outputs': ("", "ERROR"), 'process': ex}

    print("*" * 80)

    for key, val in results.items():
        test_passed = True
        if 'CRITICAL' in val['outputs'][0] or val['outputs'][1] or val['process'].return_code != 0:
            test_passed = False

        print(f"{key} - Passed: {test_passed}")
        if not test_passed:
            print(f"STDOUT: {val['outputs'][0]}\nSTDERR: {val['outputs'][1]}")

    print("*" * 80)


if __name__ == '__main__':
    main()
