import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { Markdown } from './Markdown'

it('keeps source heading depth below the containing section without creating a page title', () => {
  const text = '# Overview\n\n## Detail\n\n### Example\n\n#### Evidence\n\n##### Limits\n\n###### Footnote'
  const { container } = render(<Markdown text={text} />)
  for (const [index, name] of ['Overview', 'Detail', 'Example', 'Evidence', 'Limits', 'Footnote'].entries())
    expect(screen.getByRole('heading', { name, level: index + 3 })).toBeVisible()
  expect(container.querySelector('h1')).toBeNull()
  expect(text.startsWith('# Overview')).toBe(true)
})

it('normalizes a fragment starting at a deeper heading and preserves content and links', () => {
  render(<Markdown headingLevel={4} text={'### Idea\n\n#### Detail\n\n[Source](https://example.com/source)\n\n```python\n# not a heading\nprint(1)\n```'} />)
  expect(screen.getByRole('heading', { name: 'Idea', level: 4 })).toBeVisible()
  expect(screen.getByRole('heading', { name: 'Detail', level: 5 })).toBeVisible()
  expect(screen.getAllByRole('heading')).toHaveLength(2)
  expect(screen.getByRole('link', { name: 'Source' })).toHaveAttribute('href', 'https://example.com/source')
  expect(screen.getByText(/# not a heading/)).toBeVisible()
})
