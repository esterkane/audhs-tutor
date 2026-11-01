"""Synthetic image-only PDF fixture. No purchased or personal material."""

import io
import shutil
import subprocess
import textwrap
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)


def native_pdf(text: str | None = None) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
            NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    content = DecodedStreamObject()
    text = text or (
        "Table privileges and row policies are separate. "
        "PostgreSQL checks privileges before row policies. "
        "Datenbankrechte und Zeilenfilter sind getrennt."
    )
    lines = textwrap.wrap(text, width=65)
    escaped = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in lines]
    commands = (
        "BT /F1 14 Tf 40 720 Td "
        + " 0 -25 Td ".join("(" + line + ") Tj" for line in escaped)
        + " ET"
    )
    content.set_data(commands.encode("cp1252"))
    page[NameObject("/Contents")] = writer._add_object(content)
    result = io.BytesIO()
    writer.write(result)
    return result.getvalue()


def scanned_pdf(root: Path, *, mixed: bool = False, text: str | None = None) -> bytes:
    source = root / "native.pdf"
    source.write_bytes(native_pdf(text))
    subprocess.run(
        [
            shutil.which("pdftoppm") or "pdftoppm",
            "-singlefile",
            "-scale-to",
            "2000",
            str(source),
            str(root / "raster"),
        ],
        check=True,
        capture_output=True,
        timeout=20,
    )
    magic, size, maximum, pixels = (root / "raster.ppm").read_bytes().split(b"\n", 3)
    assert magic == b"P6" and maximum == b"255"
    width, height = map(int, size.split())
    assert len(pixels) == width * height * 3
    writer = PdfWriter()
    if mixed:
        writer.add_page(PdfReader(io.BytesIO(native_pdf(text))).pages[0])
    page = writer.add_blank_page(width=612, height=792)
    image = DecodedStreamObject()
    image.set_data(pixels)
    image.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(width),
            NameObject("/Height"): NumberObject(height),
            NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
            NameObject("/BitsPerComponent"): NumberObject(8),
        }
    )
    image = image.flate_encode()
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/XObject"): DictionaryObject({NameObject("/Scan"): writer._add_object(image)})}
    )
    content = DecodedStreamObject()
    content.set_data(b"q 612 0 0 792 0 0 cm /Scan Do Q")
    page[NameObject("/Contents")] = writer._add_object(content)
    result = io.BytesIO()
    writer.write(result)
    data = result.getvalue()
    assert not PdfReader(io.BytesIO(data)).pages[-1].extract_text()
    return data
