#!/usr/bin/env python

import glob
import subprocess as sp
import os.path


def main():
    role_paths = glob.glob("./roles/*")
    print(f"Found roles: {role_paths}")
    results = {}

    for role in role_paths:
        print(f"Testing {os.path.basename(role)} ...")
        process = sp.Popen(
            "PY_COLORS=0 molecule test --all",
            cwd=role, shell=True, stdout=sp.PIPE, stderr=sp.PIPE, text=True)
        results[os.path.basename(role)] = {
            'outputs': process.communicate(), 'process': process}

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
