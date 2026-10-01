export const activities = [
  {
    id: 'scratch',
    title: 'Free experiment',
    task: 'Write a small Python experiment. Predict what it will print, then run it.',
    code: 'message = "Hello, playground"\nprint(message)\n',
    checks: [],
  },
  {
    id: 'worked',
    title: '1. Read a worked example',
    task: 'Predict the output. Run the example, then change one input and explain what changes.',
    code: 'records = ["  Ada  ", "", " Lin "]\n\ndef clean(records):\n    return [name.strip() for name in records if name.strip()]\n\nresult = clean(records)\nprint(result)\n',
    checks: [],
  },
  {
    id: 'complete',
    title: '2. Complete the transformation',
    task: 'Complete clean(): remove surrounding spaces and skip empty names. Return the cleaned list. Try it before asking for a hint.',
    code: 'records = ["  Ada  ", "", " Lin "]\n\ndef clean(records):\n    # Build and return a list of non-empty, stripped names.\n    return records\n\nprint(clean(records))\n',
    checks: [
      {
        name: 'trim',
        criterion: 'Removes surrounding spaces',
        code: 'assert clean([" Ada "]) == ["Ada"], "Check surrounding spaces"',
      },
      {
        name: 'empty',
        criterion: 'Skips empty and whitespace-only inputs',
        code: 'assert clean(["", "  ", "Lin"]) == ["Lin"], "Check empty inputs"',
      },
      {
        name: 'order',
        criterion: 'Preserves order and handles an empty list',
        code: 'assert clean([]) == [] and clean([" B ", " A "]) == ["B", "A"], "Check order and empty lists"',
      },
    ],
  },
  {
    id: 'independent',
    title: '3. Build a new transformation',
    task: 'Write normalize_tags(tags): strip spaces, lowercase tags, remove blanks and remove duplicates while preserving first-seen order. Predict the example output before running.',
    code: 'def normalize_tags(tags):\n    # Your implementation here\n    return tags\n\nprint(normalize_tags([" AI ", "ai", "", "Python", " python "]))\n',
    checks: [
      {
        name: 'normalize',
        criterion: 'Trims and lowercases',
        code: 'assert normalize_tags([" AI ", "Python"]) == ["ai", "python"], "Check normalization"',
      },
      {
        name: 'deduplicate',
        criterion: 'Removes blanks and duplicates in first-seen order',
        code: 'assert normalize_tags(["B", "a", "b", " ", "A"]) == ["b", "a"], "Check order and duplicates"',
      },
      {
        name: 'empty',
        criterion: 'Handles no input',
        code: 'assert normalize_tags([]) == [], "Check empty input"',
      },
    ],
  },
]
export type Activity = (typeof activities)[number]
