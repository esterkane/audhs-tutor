import { Component, type ReactNode } from 'react'
/** A failed optional renderer must not remove the text, controls or assessment. */
export class VisualFallback extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    return this.state.failed
      ? <p role="status">The diagram is unavailable. Continue with the equivalent information flow and values below.</p>
      : this.props.children
  }
}
