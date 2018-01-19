import re

def do_calculations():
    document = XSCRIPTCONTEXT.getDocument() 
    sheet = document.getSheets().getByIndex(0)
    cellrange = sheet.getCellRangeByName("A1:A10000")
    row_tuples = cellrange.getDataArray()
    row = 1
    for row_tuple in row_tuples:
        if row_tuple:
            row = output_values(row, row_tuple[0], sheet)

def output_values(row, pair_string, sheet):
    """
    Multiply pairs of values by 4 and output each pair to B column.
    :param row: the row number in the B column
    :param pair_string: a string like "(123, 456)"
    :param sheet: the current spreadsheet
    Returns the next row number in the B column.
    """
    pairs = re.findall(r'\([^)]+\)', pair_string)
    for pair in pairs:
        match_obj = re.match(r'\((\d+),\s*(\d+)\)', pair)
        x, y = match_obj.groups()
        result = "(%d,%d)" % (int(x) * 4, int(y) * 4)

        cell = sheet.getCellRangeByName("B" + str(row))
        cell.setString(result)
        row += 1
    return row

# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = do_calculations,
