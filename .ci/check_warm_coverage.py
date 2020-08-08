import subprocess
import argparse
from pathlib import Path
import importlib.util

import sys
sys.path.append('.')
sys.path.append('../')

import logging

import find_local_dependencies

def find_source(fq: str) -> Path:
    """Given a string like package.module.Class.func, it finds the source file """
    names = fq.split(".")
    i = len(names)
    while(i > 0):
        toSearch = ".".join(names[0:i])
        try:
            logging.debug(f"Searching for file source: {toSearch}")
            return importlib.util.find_spec(toSearch).origin
        except ModuleNotFoundError:
            i = i - 1
            pass

def check_file_for_test_coverage(filepath: Path, threshold: int):
    """Checks a file for test coverage using existing coverage data"""
    logging.debug(f"Checking {filepath} for test coverage threshold: {threshold}")
    process = subprocess.run(["coverage", "report", f"--fail-under={threshold}", filepath])
    returncode = process.returncode
    if (returncode != 0):
        logging.warning(f"{filepath} fails test coverage check. Exit Code: {returncode} ")
        exit(returncode)
    else:
        logging.debug(f"{filepath} satisfies test coverage threshold {threshold} ")
    

def check_module_for_warm(module_path: str, threshold: int):
    for imported_name, used_name in find_local_dependencies.get_dependencies(module_path):
        filepath = find_source(f"{imported_name}.{used_name}")
        # logging.info(imported_name, used_name, filepath)
        check_file_for_test_coverage(filepath, threshold)




parser = argparse.ArgumentParser(description='Checks for warm coverage threshold.')
parser.add_argument('--threshold', '-t', nargs='?', help='Warm Coverage threshold', type=int, default=90)
parser.add_argument('--hot', nargs='?', help='Hot directory path', type=str, default="hot")
args = parser.parse_args()
check_module_for_warm(args.hot, args.threshold)
print(f"Warm Coverage is Satisfied with threshold {args.threshold}")

