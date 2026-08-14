import { Link, useParams } from 'react-router-dom'
import { api, useApi } from '../api/client'
import type { ResearchResponse } from '../api/types'
import { usePortfolioVariant } from '../App'
import { InformationClassBadge } from '../components/shared/InformationClassBadge'
import { ErrorState, LoadingState } from '../components/shared/States'
import { WhyDrillDown } from '../components/shared/WhyDrillDown'

const DEMO_ASSETS = [
  { id: 'entity:uk-bank-equity', label: 'UK Banks' },
  { id: 'entity:uk-gilts', label: 'UK Gilts' },
  { id: 'entity:us-tech-equity', label: 'US Technology' },
  { id: 'entity:eu-industrial-equity', label: 'EU Industrials' },
  { id: 'entity:cash-gbp', label: 'GBP Cash' },
]

function AssetPicker() {
  return (
    <div>
      <h1>Research</h1>
      <p className="muted">Select a holding to research, or an unlisted asset to see the "unavailable analysis" state.</p>
      <div className="scenario-picker">
        {DEMO_ASSETS.map((a) => (
          <Link key={a.id} className="scenario-picker__button" to={`/research/${encodeURIComponent(a.id)}`}>
            {a.label}
          </Link>
        ))}
        <Link className="scenario-picker__button" to="/research/entity:unlisted-example">
          Unlisted example
        </Link>
      </div>
    </div>
  )
}

export function ResearchScreen() {
  const { assetId } = useParams<{ assetId: string }>()
  const { portfolio } = usePortfolioVariant()
  const state = useApi<ResearchResponse | null>(
    () => (assetId ? api.research(assetId, portfolio) : Promise.resolve(null)),
    [assetId, portfolio],
  )

  if (!assetId) return <AssetPicker />
  if (state.status === 'loading') return <LoadingState label="Loading research…" />
  if (state.status === 'error') return <ErrorState message={state.error} />
  const d = state.data
  if (!d) return <AssetPicker />

  if (!d.covered) {
    return (
      <div>
        <h1>Research: {assetId}</h1>
        <div className="panel">
          <p>{d.message}</p>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h1>Research: {d.label}</h1>

      <div className="panel">
        <h3>Current state</h3>
        {d.current_state && (
          <>
            <p>
              Weight: {(d.current_state.result.weight * 100).toFixed(1)}% — £
              {d.current_state.result.value.toLocaleString()}
            </p>
            <InformationClassBadge informationClass={d.current_state.information_class} />
            <WhyDrillDown uapId={d.current_state.id} portfolio={portfolio} />
          </>
        )}
      </div>

      <div className="panel">
        <h3>Fundamentals</h3>
        <p className="faint">{d.fundamentals?.note}</p>
      </div>

      <div className="panel">
        <h3>Forecasts</h3>
        {d.forecasts?.map((f) => (
          <p key={f.id}>
            {f.subject}: {(f.result * 100).toFixed(2)}% <InformationClassBadge informationClass={f.information_class} />
          </p>
        ))}
      </div>

      <div className="panel">
        <h3>Scenarios</h3>
        {Object.keys(d.scenarios ?? {}).length === 0 ? (
          <p className="muted">Not modelled for this asset.</p>
        ) : (
          Object.values(d.scenarios ?? {}).map((s) => (
            <div key={s.id}>
              {s.result} <WhyDrillDown uapId={s.id} portfolio={portfolio} />
            </div>
          ))
        )}
      </div>

      <div className="panel">
        <h3>Risk</h3>
        {d.risk && (
          <p>
            Monthly volatility (std dev): {(d.risk.result * 100).toFixed(2)}%{' '}
            <InformationClassBadge informationClass={d.risk.information_class} />
          </p>
        )}
      </div>

      <div className="panel">
        <h3>Causal exposures</h3>
        {d.causal_exposures?.length === 0 && <p className="muted">No causal exposures registered for this asset.</p>}
        {d.causal_exposures?.map((c) => (
          <p key={c.id}>
            {c.subject} <InformationClassBadge informationClass={c.information_class} />
          </p>
        ))}
      </div>

      <div className="panel">
        <h3>News &amp; events</h3>
        <p className="faint">{d.news_events?.note}</p>
      </div>

      <div className="panel">
        <h3>{d.label} + You</h3>
        {d.asset_plus_you && (
          <>
            <p>Current portfolio exposure: {(d.asset_plus_you.current_portfolio_exposure * 100).toFixed(1)}%</p>
            <p>
              If £{d.asset_plus_you.if_10000_invested.additional_amount.toLocaleString()} invested:{' '}
              {(d.asset_plus_you.if_10000_invested.exposure_after * 100).toFixed(1)}%
            </p>
            {d.asset_plus_you.limitations.map((l) => (
              <p key={l} className="faint">
                {l}
              </p>
            ))}
          </>
        )}
      </div>
    </div>
  )
}
