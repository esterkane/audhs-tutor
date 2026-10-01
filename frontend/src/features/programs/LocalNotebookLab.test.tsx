import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { renderApp, jsonResponse } from '../../test/utils'
import { LocalNotebookLab } from './LocalNotebookLab'
afterEach(() => vi.unstubAllGlobals())
it('offers explicit setup and opens only the prepared course', async () => {
  const fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/status'))
      return jsonResponse({ status: 'idle', message: 'Ready to prepare', url: null, course_id: '' })
    const body = JSON.parse(init?.body as string)
    expect(body.course_id).toBe('test')
    expect(init?.headers).toMatchObject({ 'X-Notebook-Action': 'start' })
    return jsonResponse(
      body.install
        ? {
            status: 'ready',
            message: 'Ready',
            url: 'http://127.0.0.1:8890/lab/tree/test/task.ipynb?token=fixture',
            course_id: 'test',
          }
        : { status: 'needs_install', message: 'Install once', url: null, course_id: 'test' },
    )
  })
  vi.stubGlobal('fetch', fetcher)
  renderApp(<LocalNotebookLab courseId="test" />)
  await screen.findByText('Ready to prepare')
  expect(fetcher).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByRole('button', { name: 'Prepare and start notebook lab' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Install notebook tools and start lab' }))
  await waitFor(() =>
    expect(screen.getByRole('link', { name: 'Open prepared notebook in Jupyter' })).toHaveAttribute(
      'href',
      expect.stringContaining('/test/task.ipynb'),
    ),
  )
})
