import type { LabSqlResult } from '../types'
const ROLES = ['authenticated', 'anon', 'postgres'] as const

export interface ConsolePreset {
  sql: string
  role: (typeof ROLES)[number]
  sub: string
}

/** The first ```sql block of a lab README (its evidence query) as console settings. READMEs are written for
 *  psql (begin; set local role ...; set_config claims; ...; rollback;) — the console sets role and claims
 *  itself and refuses transaction control, so those wrappers become fields. */
export function consolePreset(scenario: string): ConsolePreset | null {
  const block = /```sql\n([\s\S]*?)```/.exec(scenario)?.[1]
  if (!block) return null
  const roleMatch = /set\s+local\s+role\s+(\w+)/i.exec(block)?.[1]
  const role = (ROLES as readonly string[]).includes(roleMatch ?? '')
    ? (roleMatch as ConsolePreset['role'])
    : 'postgres'
  const sub = /"sub"\s*:\s*"([^"]+)"/.exec(block)?.[1] ?? ''
  const sql = block
    .replace(/select\s+set_config\(\s*'request\.jwt\.claims'[\s\S]*?\)\s*;/gi, '')
    .replace(/^\s*(begin|commit|rollback|end)\s*;\s*$/gim, '')
    .replace(/^\s*set\s+local\s+role\s+\w+\s*;\s*$/gim, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
  return { sql, role, sub }
}

/** Markdown summary of a console result, for the learner to send to the tutor as evidence. */
export function resultSummary(sql: string, role: string, sub: string, r: LabSqlResult): string {
  const lines = [`Lab-Konsole (Rolle ${role}${sub ? `, sub ${sub}` : ''}):`, '```sql', sql.trim(), '```']
  if (r.refused) lines.push(`Abgelehnt: ${r.reason}`)
  else if (!r.ok) lines.push(`Fehler ${r.sqlstate}: ${r.message}${r.hint ? ` (Hint: ${r.hint})` : ''}`)
  else {
    const rows = r.rows ?? []
    lines.push(`${rows.length} Zeile(n)${r.truncated ? ' (gekürzt)' : ''}, ${r.ms} ms`)
    if (rows.length) {
      const cols = Object.keys(rows[0])
      lines.push(`| ${cols.join(' | ')} |`, `|${cols.map(() => '---').join('|')}|`)
      for (const row of rows.slice(0, 5)) lines.push(`| ${cols.map((c) => String(row[c])).join(' | ')} |`)
    }
  }
  const plan = r.plan?.[0]
  if (plan) lines.push(`Plan: ${plan.Plan['Node Type']}, Execution Time ${plan['Execution Time']} ms`)
  return lines.join('\n')
}
