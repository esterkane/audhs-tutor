import type { TutorRequest } from '../playground/api'

export type CountAttachment = NonNullable<TutorRequest['group_counts']>
export function readCountAttachment(value: unknown): CountAttachment | null {
  if (!value || typeof value !== 'object' || !('groups' in value) || !Array.isArray(value.groups)) return null
  const rows = value.groups
  if (
    rows.length < 2 ||
    rows.length > 8 ||
    !rows.every(
      (row) =>
        row &&
        typeof row.label === 'string' &&
        row.label.trim().length > 0 &&
        row.label.length <= 80 &&
        Number.isSafeInteger(row.before) &&
        Number.isSafeInteger(row.after) &&
        row.before >= 0 &&
        row.before <= 1e9 &&
        row.after >= 0 &&
        row.after <= row.before,
    )
  )
    return null
  if (new Set(rows.map((row) => row.label.trim())).size !== rows.length) return null
  return { groups: rows.map((row) => ({ label: row.label.trim(), before: row.before, after: row.after })) }
}
