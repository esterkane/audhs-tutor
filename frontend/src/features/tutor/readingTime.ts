/** A transparent display estimate, not a learner pace, deadline or model prediction. */
export function readingMinutes(markdown: string): number | null {
  let fence: { char: string; size: number } | null = null
  const prose: string[] = []
  for (const line of markdown.split('\n')) {
    const marker = /^ {0,3}(`{3,}|~{3,})(.*)/.exec(line)
    if (marker) {
      if (!fence) fence = { char: marker[1][0], size: marker[1].length }
      else if (marker[1][0] === fence.char && marker[1].length >= fence.size && !marker[2].trim()) fence = null
      continue
    }
    if (!fence && !/^(?: {4}|\t)/.test(line) && !/^ {0,3}#{1,6}(?:[\t ]|$)/.test(line)) prose.push(line)
  }
  const text = prose.join('\n')
    .replace(/\$\$[\s\S]*?\$\$/g, ' ')
    .replace(/`+[^`\n]*`+/g, ' ')
    .replace(/!?\[([^\]\n]{0,500})\]\([^\n)]{0,2048}\)/g, '$1')
    .replace(/https?:\/\/\S+/g, ' ')
    .replace(/^ {0,3}\[[^\]\n]+\]:.*$/gm, ' ')
  // This word-based heuristic does not estimate unsegmented CJK prose reliably.
  if (/[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]/u.test(text)) return null
  const words = text.match(/[\p{L}\p{N}]+(?:['’-][\p{L}\p{N}]+)*/gu)?.length ?? 0
  return words ? Math.max(1, Math.ceil(words / 200)) : null
}
