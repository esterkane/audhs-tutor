"""Bounded, local CPU OCR for image-only PDF pages; no hosted or tutor-model calls."""

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


class PdfOcrError(RuntimeError):
    code = "pdf_ocr_failed"


class PdfOcrUnavailable(PdfOcrError):
    code = "pdf_ocr_unavailable"


class PdfOcrLimit(PdfOcrError):
    code = "pdf_ocr_limit"


@dataclass(frozen=True)
class PdfOcrOptions:
    languages: str = "eng+deu"
    max_pages: int = 40
    timeout_s: float = 120
    max_side: int = 3000


def visible_pages(data: bytes, pages: list[int], options: PdfOcrOptions) -> list[int]:
    """Confirm rendered marks on textless authoring pages without producing source text."""
    if len(pages) > options.max_pages:
        raise PdfOcrLimit(f"Upload at most {options.max_pages} visual pages at a time.")
    executable = shutil.which("pdftoppm")
    if not executable:
        raise PdfOcrUnavailable("Install Poppler to inspect visual PDF pages.")
    deadline = time.monotonic() + options.timeout_s
    marked = []
    with tempfile.TemporaryDirectory(prefix="audhs-pdf-visual-") as folder:
        source = Path(folder) / "source.pdf"
        source.write_bytes(data)
        for page in pages:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise PdfOcrLimit("PDF page inspection timed out. Upload a smaller section.")
            try:
                raster = subprocess.run(
                    [
                        executable,
                        "-f",
                        str(page),
                        "-l",
                        str(page),
                        "-singlefile",
                        "-scale-to",
                        "1024",
                        str(source),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=min(12.0, remaining),
                ).stdout
            except subprocess.TimeoutExpired:
                raise PdfOcrLimit(
                    "PDF page inspection timed out. Upload a smaller section."
                ) from None
            except (OSError, subprocess.CalledProcessError):
                raise PdfOcrError("Local PDF page inspection failed.") from None
            magic, size, maximum, pixels = raster.split(b"\n", 3)
            width, height = map(int, size.split())
            if magic != b"P6" or maximum != b"255" or len(pixels) != width * height * 3:
                raise PdfOcrError("Local PDF page inspection returned an invalid image.")
            if pixels.count(255) != len(pixels):
                marked.append(page)
    return marked


def ocr_pages(data: bytes, pages: list[int], options: PdfOcrOptions) -> dict[int, str]:
    """Recognize selected 1-based pages, with one bounded raster in memory/on disk at a time."""
    if len(pages) > options.max_pages:
        raise PdfOcrLimit(
            f"This PDF needs OCR on {len(pages)} pages. Upload at most {options.max_pages} scanned pages at a time."
        )
    render, recognize = shutil.which("pdftoppm"), shutil.which("tesseract")
    if not render or not recognize:
        raise PdfOcrUnavailable(
            "Local PDF OCR needs Poppler and Tesseract with the configured language packs on the backend machine."
        )
    deadline = time.monotonic() + options.timeout_s

    def run(args: list[str]) -> str:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise PdfOcrLimit("PDF OCR timed out. Upload fewer pages or a clearer scan.")
        try:
            result = subprocess.run(
                args,
                check=True,
                capture_output=True,
                timeout=min(30.0, remaining),
                env={**os.environ, "OMP_THREAD_LIMIT": "1"},
            )
            return result.stdout.decode("utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            raise PdfOcrLimit("PDF OCR timed out. Upload fewer pages or a clearer scan.") from None
        except (OSError, subprocess.CalledProcessError):
            raise PdfOcrError(
                "Local PDF OCR could not read these pages. Try a clearer scan or a text export."
            ) from None

    available = set(run([recognize, "--list-langs"]).splitlines())
    if not set(options.languages.split("+")).issubset(available):
        raise PdfOcrUnavailable(
            "OCR language packs are missing. Install the packs selected by PDF_OCR_LANGUAGES on the backend."
        )
    # Detect orientation on rendered pixels; Poppler already applies PDF rotation metadata.
    segmentation = "1" if "osd" in available else "3"
    results: dict[int, str] = {}
    with tempfile.TemporaryDirectory(prefix="audhs-pdf-ocr-") as folder:
        root = Path(folder)
        source, output = root / "source.pdf", root / "page"
        source.write_bytes(data)
        for page in pages:
            run(
                [
                    render,
                    "-f",
                    str(page),
                    "-l",
                    str(page),
                    "-singlefile",
                    "-scale-to",
                    str(options.max_side),
                    "-png",
                    str(source),
                    str(output),
                ]
            )
            image = output.with_suffix(".png")
            results[page] = run(
                [recognize, str(image), "stdout", "-l", options.languages, "--psm", segmentation]
            ).strip()
            image.unlink(missing_ok=True)
            if sum(len(text) for text in results.values()) > 120000:
                raise PdfOcrLimit("OCR text exceeds 120,000 characters. Upload a smaller section.")
    return results
