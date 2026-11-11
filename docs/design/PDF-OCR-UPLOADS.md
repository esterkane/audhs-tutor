# Local OCR for scanned PDF uploads

Knowledge material uploads accept native-text, scanned and mixed PDFs. Existing selectable
text is extracted first. Pages with images and fewer than 80 extracted characters also receive
local CPU OCR, including scans that have a short selectable header. The loader recognizes raster images stored as page resources and images painted inline in a page content stream. A header missed by OCR is
retained. Blank pages without images do not require OCR. Text-rich pages are not rasterized.

The upload result identifies OCR page numbers. The learner can edit the extracted content
before saving, researching, writing or activating a lesson. OCR is transcription, not a factual
review; check names, quantities, formulas and SQL identifiers against the original. There is no
automatic grading, mastery update, execution of source content or acceptance of an OCR result.
Handwriting, complex diagrams and accurate reconstruction of table/layout semantics are not
guaranteed. The original PDF bytes and SHA-256 remain unchanged and retained privately.

## Backend setup

Install on the machine running the backend. For Ubuntu/WSL:

```sh
sudo apt-get install poppler-utils tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu
```

Other platforms need `pdftoppm`, `tesseract` and the selected language packs on the backend PATH.
The normal tutor model, embedding model and hosted authoring budget do not change. OCR does not
send documents to a hosted service or use the tutor GPU. It uses Tesseract's installed language
data, not the registry-routed generative vision service.

Settings in `.env.example`:

- `PDF_OCR_ENABLED=true` enables automatic OCR for uploads.
- `PDF_OCR_LANGUAGES=eng+deu` selects installed packs; names are joined with `+`.
- `PDF_OCR_MAX_PAGES=40` limits the number of pages needing OCR, rather than native text pages.
- `PDF_OCR_TIMEOUT_S=120` bounds total OCR work; each subprocess is also limited to 30 seconds.

The existing 10 MiB upload and 120,000-character text limits still apply. Rendering processes
one page at a time at a maximum 3,000-pixel side; Tesseract uses one OpenMP thread. Temporary
rasters are removed when work finishes or fails. The UI keeps existing writing if extraction
fails. Missing tools/languages, timeouts or page limits produce actionable errors; a mixed PDF
does not silently succeed with only its native pages when its scanned pages could not be read.

Successful extraction records engine, languages, page numbers, empty OCR pages, elapsed time
and the original content hash in a private `.pdf.extraction-<hash>.json` sidecar beside the original.
A changed transcription creates a new document version while keeping the original SHA and earlier source chunks. These files, uploads and test results are excluded from publication. Page headings still link
chunks to the original PDF page. The extracted content retains the ordinary untrusted-source
boundary; no OCR text becomes application instructions.

## Verification

Backend tests use a generated image-only PDF and a mixed PDF, real Poppler/Tesseract, native
text preservation, short selectable headers, exact original hashes and source upload responses.
Failure cases cover unavailable tools/languages, disabled OCR, page limits and process failures.
Backend CI installs the local OCR runtime and exercises those real recognition tests.

The focused browser journey can run with `AUDHS_TEST_PDF_OCR=1`. It rasterizes the same
synthetic reference passage into a genuine image-only PDF, verifies OCR and extracted content,
then runs Source → Research → Write → Review → activate → reading/prediction/notes → practice,
feedback and resume. The ordinary text-upload journey remains a separate CI run. All data is
isolated test learner data and hosted providers are off.
