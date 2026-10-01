"""External converters for formats no stdlib parser can read. Everything here is optional and
discovered on the machine, never downloaded: macOS `textutil` (legacy `.doc`, `.webarchive`),
LibreOffice `soffice` (`.doc`/`.ppt`/`.pages`/`.key` → docx/pptx), `ffmpeg` or macOS `afconvert`
(media → 16 kHz mono WAV), macOS `sips` (image formats → PNG). A missing tool means the file is
reported as skipped with the tool named — nothing fails silently."""

import platform
import shutil
import subprocess
from pathlib import Path

EXTRA_PATHS = (
    "/opt/homebrew/bin",
    "/usr/local/bin",
    "/Applications/LibreOffice.app/Contents/MacOS",
)
TIMEOUT_S = 600


def find_tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for base in EXTRA_PATHS:
        cand = Path(base) / name
        if cand.exists():
            return str(cand)
    return None


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT_S, check=False)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).decode("utf-8", "replace")[-400:]
        raise RuntimeError(f"{Path(cmd[0]).name} failed ({proc.returncode}): {tail.strip()}")


# ----------------------------------------------------------------------------- legacy office
def legacy_office_tool() -> str | None:
    if find_tool("soffice"):
        return "soffice"
    if platform.system() == "Darwin" and find_tool("textutil"):
        return "textutil"
    return None


def convert_legacy_office(src: Path, workdir: Path) -> Path:
    """`.doc` → `.docx` / `.ppt` → `.pptx` with LibreOffice; `.doc`/`.webarchive` → `.txt` with
    textutil (macOS). Returns the converted file; raises RuntimeError with the missing tool."""
    suffix = src.suffix.lower()
    soffice = find_tool("soffice")
    if soffice:
        target_fmt = {
            ".doc": "docx",
            ".ppt": "pptx",
            ".pages": "docx",
            ".key": "pptx",
            ".rtfd": "docx",
            ".wpd": "docx",
            ".numbers": "xlsx",
            ".xls": "xlsx",
        }.get(suffix)
        if target_fmt is None:
            raise RuntimeError(f"no LibreOffice target for {suffix}")
        _run(
            [soffice, "--headless", "--convert-to", target_fmt, "--outdir", str(workdir), str(src)]
        )
        out = workdir / f"{src.stem}.{target_fmt}"
        if not out.exists():
            raise RuntimeError("soffice produced no output")
        return out
    textutil = find_tool("textutil") if platform.system() == "Darwin" else None
    if textutil and suffix in (".doc", ".webarchive", ".rtfd", ".wordml"):
        out = workdir / f"{src.stem}.txt"
        _run([textutil, "-convert", "txt", "-output", str(out), str(src.resolve())])
        return out
    raise RuntimeError(
        f"{suffix} needs LibreOffice (`brew install --cask libreoffice`) or an export to "
        f"{'.docx/.pdf' if suffix in ('.doc', '.pages', '.wpd') else '.pptx/.pdf'}"
    )


# ----------------------------------------------------------------------------- media
AFCONVERT_OK = {
    ".mp3",
    ".m4a",
    ".m4b",
    ".aac",
    ".wav",
    ".aif",
    ".aiff",
    ".caf",
    ".mp4",
    ".m4v",
    ".mov",
    ".flac",
    ".alac",
    ".ac3",
    ".3gp",
    ".amr",
}


def find_decoder() -> str | None:
    if find_tool("ffmpeg"):
        return "ffmpeg"
    if platform.system() == "Darwin" and find_tool("afconvert"):
        return "afconvert"
    return None


def decoder_supports(decoder: str | None, suffix: str) -> bool:
    if decoder == "ffmpeg":
        return True
    if decoder == "afconvert":
        return suffix.lower() in AFCONVERT_OK
    return False


def decode_to_wav(src: Path, dst: Path, decoder: str) -> None:
    """16 kHz, mono, 16-bit PCM — what Whisper expects."""
    if decoder == "ffmpeg":
        _run(
            [
                find_tool("ffmpeg") or "ffmpeg",
                "-nostdin",
                "-loglevel",
                "error",
                "-y",
                "-i",
                f"file:{src.resolve()}",
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-acodec",
                "pcm_s16le",
                "-f",
                "wav",
                str(dst),
            ]
        )
    elif decoder == "afconvert":
        _run(
            [
                find_tool("afconvert") or "afconvert",
                "-f",
                "WAVE",
                "-d",
                "LEI16@16000",
                "-c",
                "1",
                str(src.resolve()),
                str(dst),
            ]
        )
    else:
        raise RuntimeError(f"unknown decoder {decoder}")


# ----------------------------------------------------------------------------- images
def image_to_png(src: Path, dst: Path, *, max_px: int = 1568) -> None:
    """HEIC/TIFF/BMP/WebP/GIF → PNG (macOS `sips`), also down-scaling large slides."""
    sips = find_tool("sips") if platform.system() == "Darwin" else None
    if sips is None:
        raise RuntimeError(f"{src.suffix} needs macOS `sips` or an export to PNG/JPEG")
    _run([sips, "-s", "format", "png", "-Z", str(max_px), str(src.resolve()), "--out", str(dst)])
