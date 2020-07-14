import subprocess
import find_local_dependencies

for module, prop in find_local_dependencies.get_dependencies("hot/"):
    filepath = module + "/" + prop + ".py"
    print(f"Checking {filepath} for warm coverage")
    # filepath ="core/logging.py"
    process = subprocess.run(["coverage", "report", "--fail-under=90", filepath])
    returncode = process.returncode
    print(f"Return code for {filepath} warm coverage check: ", returncode)
    exit(returncode)
