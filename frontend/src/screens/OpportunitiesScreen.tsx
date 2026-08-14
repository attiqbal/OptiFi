import { api, useApi } from '../api/client'
import type { OpportunitiesResponse } from '../api/types'
import { usePortfolioVariant } from '../App'
import { ConfidenceBadge } from '../components/shared/ConfidenceBadge'
import { CallToActionButton } from '../components/shared/SuggestedActionPill'
import { EmptyState, ErrorState, LoadingState } from '../components/shared/States'
import { WhyDrillDown } from '../components/shared/WhyDrillDown'

export function OpportunitiesScreen() {
  const { portfolio } = usePortfolioVariant()
  const state = useApi<OpportunitiesResponse>(() => api.opportunities(portfolio), [portfolio])

  if (state.status === 'loading') return <LoadingState label="Looking for opportunities…" />
  if (state.status === 'error') return <ErrorState message={state.error} />
  const d = state.data

  return (
    <div>
      <h1>Opportunities</h1>
      {d.opportunities.length === 0 ? (
        <EmptyState message={d.no_opportunities_message ?? 'No new opportunities today.'} />
      ) : (
        d.opportunities.map((o) => (
          <div className="card" key={o.headline}>
            <h3>{o.headline}</h3>
            <p>{o.description}</p>
            <CallToActionButton action={o.call_to_action} />
            <ConfidenceBadge breakdown={o.confidence} />
            <WhyDrillDown uapId={o.fact.id} portfolio={portfolio} />
          </div>
        ))
      )}
    </div>
  )
}
