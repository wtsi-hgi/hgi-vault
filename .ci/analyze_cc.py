



import argparse
import json
import sys






def collect_complex_blocks(data, threshold):
    total_complex_blocks = []
    num_complex_blocks = 0
    for filename, list_of_blocks in data.items():
        complex_blocks = []
        for block in list_of_blocks:
            if block["complexity"] > threshold:
                print(f"Exceeded complexity:  {filename} : {block}")
                sys.exit(1)
                complex_blocks.append(block)
                num_complex_blocks = num_complex_blocks + 1
        if len(complex_blocks) > 0:
            total_complex_blocks.append({filename: complex_blocks})
    return total_complex_blocks




def check_complexity_file(filename, threshold):
    with open(filename, "r") as read_file:
        data = json.loads(read_file.read())
        complex_blocks = collect_complex_blocks(data, threshold)
        # if len(complex_blocks) > 0:
            # sys.exit(1)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Checks for cyclomatic complexity thresholds.')
    parser.add_argument('--file', '-f', nargs='?', help='input file name', default=".ci/cyclomatic_analysis")
    parser.add_argument('--threshold', '-t', nargs='?', help='Complexity threshold', type=int, default=5)
    args = parser.parse_args()
    check_complexity_file(args.file, args.threshold)


