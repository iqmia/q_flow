"""Narrow OOXML finalization for CashflowPot Excel parity.

XlsxWriter owns workbook creation. This module only fixes details that need exact
parity with the approved Flutter report: force-formula recalculation metadata and
absolute chart geometry in EMUs.
"""

from io import BytesIO
import re
from zipfile import ZIP_DEFLATED, ZipFile


_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_CHART_URI = "http://schemas.openxmlformats.org/drawingml/2006/chart"
_CHART_WIDTH = 4_680_000
_CHART_HEIGHT = 2_880_000
_FIRST_CHART_X = 90_000
_SECOND_CHART_X = 4_860_000
_CHART_Y = 4_179_400


def _relationship_ids(rels_xml: str) -> list[str]:
    matches = re.findall(
        r'<Relationship\b[^>]*Id="([^"]+)"[^>]*Target="\.\./charts/chart([0-9]+)\.xml"[^>]*/>',
        rels_xml,
    )
    return [relationship_id for relationship_id, _ in sorted(matches, key=lambda item: int(item[1]))]


def _chart_anchor(*, relationship_id: str, name: str, object_id: int, x: int) -> str:
    return (
        '<xdr:absoluteAnchor>'
        f'<xdr:pos x="{x}" y="{_CHART_Y}"/>'
        f'<xdr:ext cx="{_CHART_WIDTH}" cy="{_CHART_HEIGHT}"/>'
        '<xdr:graphicFrame macro="">'
        '<xdr:nvGraphicFramePr>'
        f'<xdr:cNvPr id="{object_id}" name="{name}"/>'
        '<xdr:cNvGraphicFramePr/>'
        '</xdr:nvGraphicFramePr>'
        '<xdr:xfrm><a:off x="0" y="0"/>'
        f'<a:ext cx="{_CHART_WIDTH}" cy="{_CHART_HEIGHT}"/></xdr:xfrm>'
        f'<a:graphic><a:graphicData uri="{_CHART_URI}">'
        f'<c:chart xmlns:c="{_CHART_URI}" xmlns:r="{_REL_NS}" r:id="{relationship_id}"/>'
        '</a:graphicData></a:graphic>'
        '</xdr:graphicFrame><xdr:clientData/>'
        '</xdr:absoluteAnchor>'
    )


def _absolute_chart_drawing(rels_xml: str) -> str | None:
    ids = _relationship_ids(rels_xml)
    if len(ids) < 2:
        return None
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<xdr:wsDr '
        'xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        f'xmlns:r="{_REL_NS}">'
        + _chart_anchor(
            relationship_id=ids[1],
            name="Liquidity / Funding Profile",
            object_id=2,
            x=_FIRST_CHART_X,
        )
        + _chart_anchor(
            relationship_id=ids[0],
            name="Cash Movement by Period",
            object_id=3,
            x=_SECOND_CHART_X,
        )
        + '</xdr:wsDr>'
    )


def finalize_excel_ooxml(xlsx_bytes: bytes) -> bytes:
    """Return a finalized XLSX without persisting any intermediate files."""
    source = BytesIO(xlsx_bytes)
    files: dict[str, bytes] = {}
    with ZipFile(source, "r") as archive:
        for name in archive.namelist():
            files[name] = archive.read(name)

    workbook_path = "xl/workbook.xml"
    if workbook_path in files:
        xml = files[workbook_path].decode("utf-8")
        calc = '<calcPr calcId="191029" calcMode="auto" fullCalcOnLoad="1" forceFullCalc="1"/>'
        if re.search(r'<calcPr\b[^>]*/>', xml):
            xml = re.sub(r'<calcPr\b[^>]*/>', calc, xml, count=1)
        else:
            xml = xml.replace("</workbook>", f"{calc}</workbook>")
        files[workbook_path] = xml.encode("utf-8")

    rels_path = "xl/drawings/_rels/drawing1.xml.rels"
    drawing_path = "xl/drawings/drawing1.xml"
    if rels_path in files and drawing_path in files:
        drawing = _absolute_chart_drawing(files[rels_path].decode("utf-8"))
        if drawing:
            files[drawing_path] = drawing.encode("utf-8")

    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()
