"""CashflowPot backend report generators."""

# XlsxWriter exposes ``Worksheet.print_area``. Keep the report module's
# descriptive ``set_print_area`` call compatible without wrapping workbook
# objects or adding a second spreadsheet dependency.
from xlsxwriter.worksheet import Worksheet

if not hasattr(Worksheet, "set_print_area"):
    Worksheet.set_print_area = Worksheet.print_area
