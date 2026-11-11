import io
import zlib

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.knowledge.ingest.loaders import load_file
from app.knowledge.ingest.pdf_ocr import PdfOcrOptions
from tests.pdf_scan_fixture import native_pdf, scanned_pdf
from tests.test_pdf_ocr import runtime


@runtime
def test_inline_scan_in_mixed_pdf_keeps_real_page_number(tmp_path):
    # PDF pages can paint raster pixels directly with BI/ID/EI, without XObjects.
    original = PdfReader(io.BytesIO(scanned_pdf(tmp_path, text="Invoice code 42501")))
    image = original.pages[0]["/Resources"]["/XObject"]["/Scan"]
    pixels = zlib.compress(image.get_data()).hex().encode()
    writer = PdfWriter()
    writer.add_page(PdfReader(io.BytesIO(native_pdf())).pages[0])
    page = writer.add_blank_page(width=612, height=792)
    page[NameObject("/Resources")] = DictionaryObject()
    stream = DecodedStreamObject()
    stream.set_data(
        f"q 612 0 0 792 0 0 cm BI /W {image['/Width']} /H {image['/Height']} ".encode()
        + b"/CS /RGB /BPC 8 /F [/AHx /Fl] ID "
        + pixels
        + b"> EI Q"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    path = tmp_path / "inline.pdf"
    writer.write(path)
    result = load_file(path, pdf_ocr=PdfOcrOptions())
    assert [block.heading for block in result.blocks] == ["p. 1", "p. 2"]
    assert "Invoice code 42501" in result.blocks[1].text
    assert result.meta["pdf_extraction"]["ocr_pages"] == [2]
