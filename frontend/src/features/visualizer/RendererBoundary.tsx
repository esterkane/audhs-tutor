import { Component, type ReactNode } from 'react'
export class RendererBoundary extends Component<
  { children: ReactNode; onFailure: (message: string) => void },
  { failed: boolean }
> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  componentDidCatch() {
    this.props.onFailure('Rich visuals could not load. Showing the graph visual; playback is preserved.')
  }
  render() {
    return this.state.failed ? null : this.props.children
  }
}
