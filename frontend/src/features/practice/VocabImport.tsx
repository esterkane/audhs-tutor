import { useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import { DisclosureSummary } from '../../components/ui/disclosure'
import { Card } from '../../components/ui/card'
import { Textarea } from '../../components/ui/textarea'
import { useImportPreview, useImportVocab, type ImportPreviewOut } from './api'

type Row = ImportPreviewOut['rows'][number] & { removed?: boolean }

const STATUS_LABEL: Record<string, string> = {
  new: 'new card',
  exists: 'already a card',
  reverse_only: 'already a card — only the reverse card is new',
  duplicate_in_file: 'duplicate in this file',
  invalid: 'invalid',
}
const LANGS = ['de', 'en', 'es', 'fr', 'it']
const LIMITS = { word: 120, translation: 200, example: 300 }

/**
 * CSV vocabulary import (P3): preview every row with its status, edit or remove rows, choose the
 * language and whether reverse cards are wanted, then confirm explicitly. Re-importing the same
 * file adds nothing; existing schedules are never touched (kernel/vocab_import.py).
 */
export function VocabImport() {
  const previewMut = useImportPreview()
  const importMut = useImportVocab()
  const [lang, setLang] = useState('de')
  const [reverse, setReverse] = useState(false)
  const [source, setSource] = useState<string | null>(null)
  const [csvText, setCsvText] = useState('')
  const [rows, setRows] = useState<Row[] | null>(null)
  const [meta, setMeta] = useState<ImportPreviewOut | null>(null)

  const operation = useRef(false)
  const [busy, setBusy] = useState(false)
  const [fileError, setFileError] = useState<string | null>(null)

  async function runPreview(input: string | File) {
    if (operation.current) return
    operation.current = true
    setBusy(true)
    setFileError(null)
    previewMut.reset()
    importMut.reset()
    setRows(null)
    setMeta(null)
    try {
      const file = typeof input === 'string' ? null : input
      if (file && file.size > 2_000_000) {
        setFileError('File larger than 2 MB. Choose a smaller CSV file.')
        return
      }
      let text: string
      try { text = typeof input === 'string' ? input : await input.text() }
      catch { setFileError('Could not read this file. Choose it again or paste the list.'); return }
      setSource(file?.name ?? null)
      setCsvText(text)
      const pv = await previewMut.mutateAsync({ lang, csv_text: text, reverse })
      setMeta(pv)
      setRows(pv.rows.map((r) => ({ ...r })))
    } catch {
      /* previewMut.error is rendered */
    } finally {
      operation.current = false
      setBusy(false)
    }
  }

  const active = (rows ?? []).filter((r) => !r.removed)
  const importable = active.filter(
    (r) => (r.status === 'new' || r.status === 'reverse_only') && r.word.trim() && r.translation.trim(),
  )
  const locked = busy || rows !== null // language and direction were used for the preview: re-preview to change

  async function confirm() {
    if (operation.current || importable.length === 0) return
    operation.current = true
    setBusy(true)
    try {
      await importMut.mutateAsync({
        lang,
        reverse,
        source,
        rows: importable.map((r) => ({
          word: r.word,
          translation: r.translation,
          example: r.example ?? null,
        })),
      })
    } catch {
      /* A lost response does not establish whether the server committed. */
    } finally {
      operation.current = false
      setBusy(false)
    }
  }

  function update(i: number, patch: Partial<Row>) {
    if (operation.current) return
    importMut.reset()
    const identityEdited = 'word' in patch || 'translation' in patch
    setRows((prev) =>
      prev
        ? prev.map((r, k) =>
            k === i
              ? { ...r, ...patch, status: identityEdited ? reStatus({ ...r, ...patch }) : r.status }
              : r,
          )
        : prev,
    )
  }

  function startOver() {
    if (operation.current) return
    previewMut.reset()
    importMut.reset()
    setFileError(null)
    setRows(null)
    setMeta(null)
  }

  return (
    <Card className="min-w-0">
      <p className="text-sm text-muted mb-3">
        Columns: word, translation, optional example (header row optional; `,` `;` or tab). Every row is shown
        with its status before anything is saved; re-importing the same file adds no cards and never changes a
        schedule — an existing card only gains an example or source if it had none. PDF glossaries can&apos;t
        be imported: export the glossary as CSV with word and translation columns.
      </p>
      <div className="flex flex-wrap gap-3 items-end">
        <label className="text-sm font-medium">
          Language
          <input
            className="block min-h-control-target w-16 border border-control rounded-md px-2 py-1 mt-1"
            value={lang}
            maxLength={8}
            list="vocab-import-langs"
            disabled={locked}
            onChange={(e) => setLang(e.target.value)}
          />
          <datalist id="vocab-import-langs">
            {LANGS.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </label>
        <label className="text-sm font-medium min-w-0">
          CSV file
          <input
            type="file"
            accept=".csv,text/csv,text/plain"
            className="block min-h-control-target mt-1 w-full min-w-0"
            disabled={busy}
            onChange={(e) => { const file = e.target.files?.[0]; if (file) void runPreview(file) }}
          />
        </label>
        <label className="text-sm font-medium flex min-h-control-target items-center gap-2">
          <input
            type="checkbox"
            checked={reverse}
            disabled={locked}
            onChange={(e) => setReverse(e.target.checked)}
          />
          Also create reverse cards (translation → word)
        </label>
        {locked && (
          <Button size="sm" variant="ghost" disabled={busy} onClick={startOver}>
            Start over (change language or direction)
          </Button>
        )}
      </div>
      <details className="mt-3 [&[open]>summary>svg]:rotate-90">
        <DisclosureSummary>Or paste the list</DisclosureSummary>
        <label htmlFor="csv-paste" className="sr-only">
          CSV text
        </label>
        <Textarea
          id="csv-paste"
          disabled={busy}
          value={csvText}
          onChange={(e) => setCsvText(e.target.value)}
          className="mt-2"
        />
        <Button
          size="sm"
          className="mt-2"
          disabled={!csvText.trim() || busy}
          onClick={() => void runPreview(csvText)}
        >
          Preview
        </Button>
      </details>
      {busy && <p role="status">{importMut.isPending ? 'Importing reviewed cards…' : 'Preparing preview…'}</p>}
      {fileError && <p role="alert">{fileError}</p>}
      {previewMut.isError && (
        <p role="alert" className="text-warn mt-2">
          {(previewMut.error as Error).message}
        </p>
      )}
      {meta && meta.errors.length > 0 && (
        <ul role="alert" className="text-warn text-sm mt-2 list-disc ml-5">
          {meta.errors.map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      )}
      {rows && rows.length === 0 && meta && meta.errors.length === 0 && (
        <p className="text-sm mt-3" role="status">
          No rows found. The file needs at least a word and a translation per line.
        </p>
      )}
      {rows && rows.length > 0 && meta && (
        <>
          <p className="text-sm mt-3">
            {meta.header ? 'Header row detected' : 'No header: first column = word, second = translation'} ·
            columns:{' '}
            {Object.entries(meta.columns)
              .map(([k, v]) => `${k} = ${v + 1}`)
              .join(', ')}{' '}
            · {importable.length} to import ({active.filter((r) => r.status === 'reverse_only').length}{' '}
            reverse only), {active.filter((r) => r.status === 'exists').length} already cards,{' '}
            {active.filter((r) => r.status === 'duplicate_in_file').length} duplicates in file,{' '}
            {active.filter((r) => r.status === 'invalid').length} invalid
          </p>
          <div className="relative overflow-x-auto mt-2" role="region" aria-label="CSV preview rows; scroll horizontally for all columns" tabIndex={0}>
            <table className="text-sm w-full min-w-max">
              <caption className="sr-only">Rows to import</caption>
              <thead>
                <tr className="text-left">
                  <th className="pr-2">Row</th>
                  <th className="pr-2">Word</th>
                  <th className="pr-2">Translation</th>
                  <th className="pr-2">Example</th>
                  <th className="pr-2">Status</th>
                  <th>
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) =>
                  r.removed ? (
                    <tr key={`${r.row}-${i}`} className="text-muted">
                      <td className="pr-2">{r.row}</td>
                      <td colSpan={4} className="pr-2">
                        Row {r.row} removed.
                      </td>
                      <td>
                        <Button
                          size="sm"
                          variant="ghost"
                          aria-label={`Undo remove row ${r.row}`}
                          disabled={busy}
                          onClick={() => update(i, { removed: false })}
                        >
                          Undo
                        </Button>
                      </td>
                    </tr>
                  ) : (
                    <tr key={`${r.row}-${i}`} className={r.status === 'invalid' ? 'text-warn' : ''}>
                      <td className="pr-2 text-muted">{r.row}</td>
                      <td className="pr-2">
                        <input
                          aria-label={`Word, row ${r.row}`}
                          disabled={busy}
                          className="min-h-control-target border border-control rounded-md px-1 w-full"
                          value={r.word}
                          maxLength={LIMITS.word}
                          onChange={(e) => update(i, { word: e.target.value })}
                        />
                      </td>
                      <td className="pr-2">
                        <input
                          aria-label={`Translation, row ${r.row}`}
                          disabled={busy}
                          className="min-h-control-target border border-control rounded-md px-1 w-full"
                          value={r.translation}
                          maxLength={LIMITS.translation}
                          onChange={(e) => update(i, { translation: e.target.value })}
                        />
                      </td>
                      <td className="pr-2">
                        <input
                          aria-label={`Example, row ${r.row}`}
                          disabled={busy}
                          className="min-h-control-target border border-control rounded-md px-1 w-full"
                          value={r.example ?? ''}
                          maxLength={LIMITS.example}
                          onChange={(e) => update(i, { example: e.target.value || null })}
                        />
                      </td>
                      <td className="pr-2">
                        {STATUS_LABEL[r.status] ?? r.status}
                        {r.problem ? ` — ${r.problem}` : ''}
                      </td>
                      <td>
                        <Button
                          size="sm"
                          variant="ghost"
                          aria-label={`Remove row ${r.row}`}
                          disabled={busy}
                          onClick={() => update(i, { removed: true })}
                        >
                          Remove
                        </Button>
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex gap-2 items-center flex-wrap">
            <Button
              variant="primary"
              disabled={importable.length === 0 || busy}
              onClick={() => void confirm()}
            >
              {importMut.isPending
                ? 'Importing…'
                : `Import ${importable.length} card${importable.length === 1 ? '' : 's'}${reverse ? ` + up to ${importable.length} reverse` : ''}`}
            </Button>
            {importMut.data && (
              <span role="status" className="text-sm">
                Imported {importMut.data.added} new card{importMut.data.added === 1 ? '' : 's'}
                {importMut.data.reverse_added ? ` and ${importMut.data.reverse_added} reverse` : ''};{' '}
                {importMut.data.skipped_existing} already existed
                {importMut.data.reverse_skipped ? ` (${importMut.data.reverse_skipped} reverse)` : ''},{' '}
                {importMut.data.duplicate_in_file ? `${importMut.data.duplicate_in_file} duplicates, ` : ''}
                {importMut.data.invalid} invalid.
              </span>
            )}
            {importMut.isError && (
              <span role="alert" className="text-warn text-sm">
                {(importMut.error as Error).message} — could not confirm the import. Your reviewed rows are kept; retrying will skip cards already saved.
              </span>
            )}
          </div>
        </>
      )}
    </Card>
  )
}

/** Identity edited: the server decides on import (an existing card → skipped_existing). */
function reStatus(r: Row): Row['status'] {
  return r.word.trim() && r.translation.trim() ? 'new' : 'invalid'
}
