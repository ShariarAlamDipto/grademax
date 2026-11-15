"use client"
import { Component, type ErrorInfo, type ReactNode } from "react"
import { COLORS, card, smallButton } from "./ui"

interface PanelBoundaryProps {
  /** Shown in the message, e.g. "Content". */
  name: string
  children: ReactNode
}

interface PanelBoundaryState {
  failed: boolean
}

/**
 * Keeps a failure inside one dashboard section. Without it, a panel that
 * throws while rendering (a report with a missing field, say) replaced the
 * whole admin page with the error screen. Give it a `key` per section so
 * switching sections starts clean.
 */
export default class PanelBoundary extends Component<PanelBoundaryProps, PanelBoundaryState> {
  state: PanelBoundaryState = { failed: false }

  static getDerivedStateFromError(): PanelBoundaryState {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error(`[admin/analytics] ${this.props.name} section failed to render:`, error, info.componentStack)
  }

  render(): ReactNode {
    if (!this.state.failed) return this.props.children
    return (
      <div role="alert" style={{ ...card, borderColor: COLORS.amber, color: "var(--gm-text-2)", fontSize: "0.85rem" }}>
        <p style={{ marginBottom: "0.75rem" }}>
          The {this.props.name} section could not be shown. The other sections still work.
        </p>
        <button type="button" onClick={() => this.setState({ failed: false })} style={smallButton}>Try again</button>
      </div>
    )
  }
}
