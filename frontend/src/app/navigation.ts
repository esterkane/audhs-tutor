export const primaryPages = [
  ['/', 'Home'], ['/library', 'Library'], ['/progress', 'Progress'], ['/projects', 'Projects'], ['/ask', 'Ask'], ['/preferences', 'Settings'],
] as const
export const toolPages = [
  ['/ask', 'Ask the tutor'],
  ['/areas', 'Prepare learning material'], ['/corpus', 'Materials'], ['/models', 'Models'], ['/experiments', 'Experiments'],
  ['/curriculum', 'Knowledge material'], ['/answers', 'Saved answers'], ['/playground', 'Playground'],
  ['/vocab', 'Vocabulary'], ['/together', 'Work alongside'],
  ['/explore', 'Explore knowledge'], ['/search', 'Search material'], ['/sources', 'Sources'],
  ['/map', 'Skill map'], ['/review', 'Review'], ['/corrections', 'Correction drafts'],
  ['/preferences', 'Preferences'],
] as const

/** One palette entry per destination, preferring the primary destination name. */
export const navigationPages = [
  ...primaryPages,
  ...toolPages.filter(([href]) => !primaryPages.some(([primary]) => primary === href)),
]
