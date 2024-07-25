"""
To generate part of letters.py

Before running this script, download the
latest Unicode database file UnicodeData.txt.
"""
import re

INFILE = "UnicodeData.txt"
OUTFILE = "out/letters2.py"
LINE_WIDTH = 79  # number of characters

class Reader:
    """Reads pairs from Unicode database file."""
    def __init__(self):
        self.case_pair_capitals = []
        self.case_pair_smalls = []

    def read(self):
        with open(INFILE, 'r') as infile:
            for line in infile:
                match = re.match(
                    r'^([0-9A-F]{4});([A-Z]+) CAPITAL LETTER ([A-Z]+);', line)
                if match:
                    code, script, letter = match.groups()
                    small_case_match = re.search(r';([0-9A-F]{4});$', line)
                    if small_case_match:
                        corresponding_small_case = small_case_match.group(1)
                        if corresponding_small_case:
                            self.case_pair_capitals.append(code)
                            self.case_pair_smalls.append(
                                corresponding_small_case)

def output_codelist(filehandle, indent_size, codelist):
    filehandle.write(" " * indent_size)
    line_x = indent_size  # how far to the right we are in printing the line
    for i, code in enumerate(codelist):
        out_str = f'"\\u{code}"'
        if i < len(codelist) - 1:
            out_str += ","
        line_x += len(out_str)
        if line_x >= LINE_WIDTH:
            filehandle.write("\n" + " " * indent_size)
            line_x = indent_size + len(out_str)
        filehandle.write(out_str)

class Writer:
    """Writes results to file."""
    def write(self, reader):
        with open(OUTFILE, 'w') as outfile:
            outfile.write("CASE_CAPITALS = [\n")
            output_codelist(outfile, 8, reader.case_pair_capitals)
            outfile.write("]\n\n")
            
            outfile.write("# lower case equivalent of CaseCapital at same index\n")
            outfile.write("CASE_LOWER = [\n")
            output_codelist(outfile, 8, reader.case_pair_smalls)
            outfile.write("]\n\n")

reader = Reader()
reader.read()
writer = Writer()
writer.write(reader)
