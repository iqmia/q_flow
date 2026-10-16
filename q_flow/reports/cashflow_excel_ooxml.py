"""Narrow OOXML finalization for CashflowPot Excel parity.

XlsxWriter owns workbook creation. This module only fixes details that need exact
parity with the approved Flutter report: force-formula recalculation metadata,
absolute chart geometry, and the optional CashflowPot logo drawing.
"""

from io import BytesIO
import re
from zipfile import ZIP_DEFLATED, ZipFile


_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_CHART_URI = "http://schemas.openxmlformats.org/drawingml/2006/chart"
_DRAWING_REL = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing"
)
_IMAGE_REL = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
)
_CHART_WIDTH = 4_680_000
_CHART_HEIGHT = 2_880_000
_FIRST_CHART_X = 90_000
_SECOND_CHART_X = 4_860_000
_CHART_Y = 4_179_400
_LOGO_X = 90_000
_LOGO_Y = 40_000
_LOGO_SIZE = 612_000
_LOGO_REL_ID = "rIdCashflowLogo"
_DRAWING_REL_ID = "rIdCashflowDrawing"


def _relationship_ids(rels_xml: str) -> list[str]:
    matches = re.findall(
        r'<Relationship\b[^>]*Id="([^"]+)"[^>]*Target="\.\./charts/chart([0-9]+)\.xml"[^>]*/>',
        rels_xml,
    )
    return [
        relationship_id
        for relationship_id, _ in sorted(matches, key=lambda item: int(item[1]))
    ]


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


def _logo_anchor() -> str:
    return (
        '<xdr:absoluteAnchor>'
        f'<xdr:pos x="{_LOGO_X}" y="{_LOGO_Y}"/>'
        f'<xdr:ext cx="{_LOGO_SIZE}" cy="{_LOGO_SIZE}"/>'
        '<xdr:pic>'
        '<xdr:nvPicPr><xdr:cNvPr id="4" name="CashFlowPot Logo"/>'
        '<xdr:cNvPicPr/></xdr:nvPicPr>'
        f'<xdr:blipFill><a:blip r:embed="{_LOGO_REL_ID}"/>'
        '<a:stretch><a:fillRect/></a:stretch></xdr:blipFill>'
        '<xdr:spPr><a:xfrm><a:off x="0" y="0"/>'
        f'<a:ext cx="{_LOGO_SIZE}" cy="{_LOGO_SIZE}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr>'
        '</xdr:pic><xdr:clientData/></xdr:absoluteAnchor>'
    )


def _absolute_drawing(rels_xml: str, *, include_logo: bool) -> str | None:
    ids = _relationship_ids(rels_xml)
    parts: list[str] = []
    if include_logo:
        parts.append(_logo_anchor())
    if len(ids) >= 2:
        parts.extend(
            [
                _chart_anchor(
                    relationship_id=ids[1],
                    name="Liquidity / Funding Profile",
                    object_id=2,
                    x=_FIRST_CHART_X,
                ),
                _chart_anchor(
                    relationship_id=ids[0],
                    name="Cash Movement by Period",
                    object_id=3,
                    x=_SECOND_CHART_X,
                ),
            ]
        )
    if not parts:
        return None
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<xdr:wsDr '
        'xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        f'xmlns:r="{_REL_NS}">'
        + "".join(parts)
        + '</xdr:wsDr>'
    )


def _append_relationship(xml: str, *, rel_id: str, rel_type: str, target: str) -> str:
    if f'Id="{rel_id}"' in xml:
        return xml
    relationship = (
        f'<Relationship Id="{rel_id}" Type="{rel_type}" Target="{target}"/>'
    )
    return xml.replace("</Relationships>", f"{relationship}</Relationships>")


def _ensure_sheet_drawing(files: dict[str, bytes]) -> None:
    """Create a worksheet drawing relationship when the workbook has no charts."""
    sheet_path = "xl/worksheets/sheet1.xml"
    rels_path = "xl/worksheets/_rels/sheet1.xml.rels"
    drawing_path = "xl/drawings/drawing1.xml"
    if drawing_path in files:
        return

    sheet = files[sheet_path].decode("utf-8")
    worksheet_tag = re.search(r'<worksheet\b[^>]*>', sheet)
    if worksheet_tag and "xmlns:r=" not in worksheet_tag.group(0):
        tag = worksheet_tag.group(0)
        replacement = tag[:-1] + f' xmlns:r="{_REL_NS}">'
        sheet = sheet.replace(tag, replacement, 1)
    if "<drawing " not in sheet:
        sheet = sheet.replace(
            "</worksheet>",
            f'<drawing r:id="{_DRAWING_REL_ID}"/></worksheet>',
        )
    files[sheet_path] = sheet.encode("utf-8")

    if rels_path in files:
        rels = files[rels_path].decode("utf-8")
    else:
        rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships '
            'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '</Relationships>'
        )
    rels = _append_relationship(
        rels,
        rel_id=_DRAWING_REL_ID,
        rel_type=_DRAWING_REL,
        target="../drawings/drawing1.xml",
    )
    files[rels_path] = rels.encode("utf-8")


def _ensure_content_types(files: dict[str, bytes], *, include_logo: bool) -> None:
    path = "[Content_Types].xml"
    xml = files[path].decode("utf-8")
    drawing = (
        '<Override PartName="/xl/drawings/drawing1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>'
    )
    if 'PartName="/xl/drawings/drawing1.xml"' not in xml:
        xml = xml.replace("</Types>", f"{drawing}</Types>")
    if include_logo and not re.search(r'<Default\b[^>]*Extension="png"', xml):
        png = '<Default Extension="png" ContentType="image/png"/>'
        xml = xml.replace("</Types>", f"{png}</Types>")
    files[path] = xml.encode("utf-8")


def finalize_excel_ooxml(xlsx_bytes: bytes, *, logo_bytes: bytes | None = None) -> bytes:
    """Return a finalized XLSX without persisting any intermediate files."""
    source = BytesIO(xlsx_bytes)
    files: dict[str, bytes] = {}
    with ZipFile(source, "r") as archive:
        for name in archive.namelist():
            files[name] = archive.read(name)

    workbook_path = "xl/workbook.xml"
    if workbook_path in files:
        xml = files[workbook_path].decode("utf-8")
        calc = (
            '<calcPr calcId="191029" calcMode="auto" '
            'fullCalcOnLoad="1" forceFullCalc="1"/>'
        )
        if re.search(r'<calcPr\b[^>]*/>', xml):
            xml = re.sub(r'<calcPr\b[^>]*/>', calc, xml, count=1)
        else:
            xml = xml.replace("</workbook>", f"{calc}</workbook>")
        files[workbook_path] = xml.encode("utf-8")

    include_logo = bool(logo_bytes)
    if include_logo:
        _ensure_sheet_drawing(files)

    rels_path = "xl/drawings/_rels/drawing1.xml.rels"
    drawing_path = "xl/drawings/drawing1.xml"
    if include_logo:
        if rels_path in files:
            rels = files[rels_path].decode("utf-8")
        else:
            rels = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships '
                'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '</Relationships>'
            )
        rels = _append_relationship(
            rels,
            rel_id=_LOGO_REL_ID,
            rel_type=_IMAGE_REL,
            target="../media/cashflowpot_logo.png",
        )
        files[rels_path] = rels.encode("utf-8")
        files["xl/media/cashflowpot_logo.png"] = bytes(logo_bytes or b"")

    if rels_path in files:
        drawing = _absolute_drawing(
            files[rels_path].decode("utf-8"), include_logo=include_logo
        )
        if drawing:
            files[drawing_path] = drawing.encode("utf-8")
            _ensure_content_types(files, include_logo=include_logo)

    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()
