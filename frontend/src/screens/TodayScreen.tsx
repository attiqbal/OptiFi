import { api, useApi } from '../api/client'
import type { TodayResponse } from '../api/types'
import { usePortfolioVariant } from '../App'
import { ConfidenceBadge } from '../components/shared/ConfidenceBadge'
import { InformationClassBadge } from '../components/shared/InformationClassBadge'
import { SuggestedActionPill } from '../components/shared/SuggestedActionPill'
import { ErrorState, LoadingState } from '../components/shared/States'
import { ValidationStatusFlag } from '../components/shared/ValidationStatusFlag'
import { WhyDrillDown } from '../components/shared/WhyDrillDown'

export function TodayScreen() {
  const { portfolio } = usePortfolioVariant()
  const state = useApi<TodayResponse>(() => api.today(portfolio), [portfolio])

  if (state.status === 'loading') return <LoadingState label="Loading today's briefing…" />
  if (state.status === 'error') return <ErrorState message={state.error} />
  const data = state.data

  return (
    <div>
      <h1>Good morning</h1>

      <div className="panel panel-grid">
        <div className="stat">
          <span className="stat__label">Portfolio value</span>
          <span className="stat__value">£{data.portfolio_value.result.toLocaleString()}</span>
          <InformationClassBadge informationClass={data.portfolio_value.information_class} />
        </div>
        <div className="stat">
          <span className="stat__label">Risk (0-10 illustrative scale)</span>
          <span className="stat__value">{data.risk.result} / 10</span>
          <InformationClassBadge informationClass={data.risk.information_class} />
        </div>
        <div className="stat">
          <span className="stat__label">
            Capital efficiency {!data.capital_efficiency.authoritative && '(provisional — not authoritative)'}
          </span>
          <span className="stat__value">{Math.round(data.capital_efficiency.result)} / 100</span>
          <InformationClassBadge informationClass={data.capital_efficiency.information_class} />{' '}
          <ValidationStatusFlag status={data.capital_efficiency.validation_status} />
        </div>
      </div>

      <h2>
        {data.developments.length} development{data.developments.length === 1 ? '' : 's'} matter
        {data.developments.length === 1 ? 's' : ''} today
      </h2>
      {data.developments.map((d) => (
        <div className="card" key={d.headline}>
          <h3>{d.headline}</h3>
          <p className="muted">Portfolio impact: {d.portfolio_impact}</p>
          {d.affected && <p className="faint">Affected: {d.affected.join(', ')}</p>}
          {d.your_exposure !== undefined && <p className="faint">Your exposure: {d.your_exposure}%</p>}
          {d.potential_annual_improvement !== undefined && (
            <p className="faint">Potential annual improvement: £{d.potential_annual_improvement.toLocaleString()}</p>
          )}
          <p>
            Suggested action: <SuggestedActionPill action={d.suggested_action} />
          </p>
          <ConfidenceBadge breakdown={d.confidence} />
          {d.evidence_ids[0] && <WhyDrillDown uapId={d.evidence_ids[0]} portfolio={portfolio} />}
        </div>
      ))}
    </div>
  )
}
