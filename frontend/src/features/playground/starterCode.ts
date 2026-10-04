export const STARTER_REQUEST = 'Suggest one small starter Python example for this lesson and explain what to try next. Propose illustrative JSON data and one task for me to implement using Python built-ins. The app will supply an unfinished function. Do not invent missing datasets, packages or credentials, or claim the code has been run.'

// Only complete, explicitly Python-tagged blocks are eligible for insertion.
export function pythonExamples(text: string): string[] {
  const blocks = [...text.matchAll(/^```(?:python|py)[ \t]*\r?\n([\s\S]*?)^```[ \t]*$/gim)]
    .map(match => match[1].trimEnd())
    .filter(code => code.trim().length > 0 && code.length <= 16000)
  return blocks.length <= 3 ? blocks : []
}

export function appendExample(current: string, example: string): string | null {
  if (!example.trim() || current.endsWith(example)) return null
  const next = current ? `${current}\n\n${example}` : example
  return next.length <= 16000 ? next : null
}
