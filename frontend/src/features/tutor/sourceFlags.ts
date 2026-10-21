export function withheldCount(dropped: string[] | undefined): number {
  return (dropped ?? []).filter((item) => item.endsWith(':quarantined')).length
}


export function hasUnsupportedCitation(flags: unknown): boolean {
  return Array.isArray(flags) && flags.includes('unsupported_numeric_citation')
}

export function hasSocraticFormatMismatch(flags: unknown): boolean {
  return Array.isArray(flags) && flags.includes('socratic_format_mismatch')
}

export const SOCRATIC_FORMAT_WARNING = 'This reply did not follow the requested Socratic format. It is kept in history but will not be reused as a teaching example. This check does not verify factual accuracy.'
