import { useState } from 'react'
import { api } from '../../api/client'
import type { PortfolioVariant, UAP } from '../../api/types'
import { InformationClassBadge } from './InformationClassBadge'
import { ValidationStatusFlag } from './ValidationStatusFlag'

/** APP_UX_BLUEPRINT.md Section 12's "Why?" drill-down: every step
 * labelled with its producing engine and information_class, any
 * non-VERIFIED status flagged, sources visible beneath — not hidden
 * behind another click. A native <details> element so it's keyboard-
 * operable and announced correctly by screen readers with no extra ARIA
 * wiring. Fetches lazily on first open, not on every render. */
export function WhyDrillDown({ uapId, portfolio }: { uapId: string; portfolio: PortfolioVariant }) {
  const [chain, setChain] = useState<UAP[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleToggle(open: boolean) {
    if (!open || chain !== null || loading) return
    setLoading(true)
    try {
      const res = await api.evidence(uapId, portfolio)
      setChain(res.chain)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load evidence.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <details className="why" onToggle={(e) => handleToggle(e.currentTarget.open)}>
      <summary>Why?</summary>
      {loading && <p className="muted">Loading evidence…</p>}
      {error && <p className="state-message--error">{error}</p>}
      {chain && (
        <div>
          {chain.map((u) => (
            <div className="why-step" key={u.id}>
              <InformationClassBadge informationClass={u.information_class} />{' '}
              <ValidationStatusFlag status={u.validation_status} />
              <div>{u.subject}</div>
              <div className="why-step__producer">{u.producer}</div>
            </div>
          ))}
        </div>
      )}
    </details>
  )
}
