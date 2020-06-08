


from core import typing as T
import json







def collect_complex_blocks(data, threshold):
    total_complex_blocks = []
    num_complex_blocks = 0
    for filename, list_of_blocks in data.items():
        complex_blocks = []
        for block in list_of_blocks:
            if block["complexity"] > threshold:
                complex_blocks.append(block)
                num_complex_blocks = num_complex_blocks + 1
        if len(complex_blocks) > 0:
            total_complex_blocks.append({filename: complex_blocks})
    return total_complex_blocks




def check_complexity_file(filename, threshold):
    with open(filename, "r") as read_file:
        data = json.loads(read_file.read())
        complex_blocks = collect_complex_blocks(data, threshold)
        print(complex_blocks)






check_complexity_file("cyclomatic_analysis", 5)
