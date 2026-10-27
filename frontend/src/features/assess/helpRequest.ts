/** Recognise explicit uncertainty, not short answers or incomplete reasoning. */
export function isHelpRequest(answer: string): boolean {
  const normal = answer.trim().toLocaleLowerCase().replace(/[’‘]/g, "'").replace(/[.!?]+$/, '').trim()
  return new Set(["i don't know", 'i do not know', 'idk', "i'm not sure", 'i am not sure',
    'not sure', 'ich weiß es nicht', 'ich weiss es nicht', 'weiß nicht', 'weiss nicht', 'keine ahnung']).has(normal)
}
