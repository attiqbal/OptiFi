import { api, useApi } from '../api/client'
import type { PortfolioResponse } from '../api/types'
import { usePortfolioVariant } from '../App'
import { InformationClassBadge } from '../components/shared/InformationClassBadge'
import { ErrorState, LoadingState } from '../components/shared/States'
import { ValidationStatusFlag } from '../components/shared/ValidationStatusFlag'
import { WhyDrillDown } from '../components/shared/WhyDrillDown'

function ExposureTable({ title, exposure }: { title: string; exposure: Record<string, number> }) {
  return (
    <div className="panel">
      <h3>{title}</h3>
      <table className="data-table">
        <tbody>
          {Object.entries(exposure).map(([k, v]) => (
            <tr key={k}>
              <td>{k}</td>
              <td>{(v * 100).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function PortfolioScreen() {
  const { portfolio } = usePortfolioVariant()
  const state = useApi<PortfolioResponse>(() => api.portfolio(portfolio), [portfolio])

  if (state.status === 'loading') return <LoadingState label="Loading portfolio…" />
  if (state.status === 'error') return <ErrorState message={state.error} />
  const d = state.data

  return (
    <div>
      <h1>Portfolio</h1>

      <div className="panel panel-grid">
        <div className="stat">
          <span className="stat__label">Total capital</span>
          <span className="stat__value">£{d.net_capital.toLocaleString()}</span>
        </div>
        <div className="stat">
          <span className="stat__label">Assets</span>
          <span className="stat__value">£{d.assets_total.toLocaleString()}</span>
        </div>
        <div className="stat">
          <span className="stat__label">Liabilities</span>
          <span className="stat__value">£{d.liabilities_total.toLocaleString()}</span>
        </div>
      </div>

      {d.data_freshness.stale_items.length > 0 && (
        <div className="panel" role="alert">
          <h3>Data freshness</h3>
          {d.data_freshness.stale_items.map((s) => (
            <p key={s.subject} className="faint">
              {s.description}
            </p>
          ))}
        </div>
      )}

      <div className="panel">
        <h3>Holdings</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Holding</th>
              <th>Sector</th>
              <th>Geography</th>
              <th>Currency</th>
              <th>Weight</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            {d.holdings.map((h) => (
              <tr key={h.entity_id}>
                <td>
                  {h.label} <InformationClassBadge informationClass={h.fact.information_class} />{' '}
                  <ValidationStatusFlag status={h.fact.validation_status} />
                </td>
                <td>{h.sector}</td>
                <td>{h.geography}</td>
                <td>{h.currency}</td>
                <td>{(h.weight * 100).toFixed(1)}%</td>
                <td>£{h.value.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel-grid">
        <ExposureTable title="Sector exposure" exposure={d.sector_exposure} />
        <ExposureTable title="Geographic exposure" exposure={d.geographic_exposure} />
        <ExposureTable title="Currency exposure" exposure={d.currency_exposure} />
      </div>

      <div className="panel">
        <h3>Concentration</h3>
        <p>
          Largest holding: {d.concentration.largest_holding} ({(d.concentration.largest_weight * 100).toFixed(1)}%)
        </p>
        {d.concentration.technology_breach && (
          <p className="faint">Technology exposure exceeds target maximum of {d.concentration.technology_target_max * 100}%.</p>
        )}
      </div>

      <div className="panel">
        <h3>Liquidity</h3>
        <p>
          Cash £{d.liquidity.actual_cash.toLocaleString()} vs. minimum reserve £
          {d.liquidity.minimum_reserve.toLocaleString()}
        </p>
      </div>

      <div className="panel">
        <h3>Risk</h3>
        <p>
          Portfolio variance <InformationClassBadge informationClass={d.risk.portfolio_variance.information_class} />
        </p>
        <div>
          95% parametric VaR: £{d.risk.parametric_var_95.result.toFixed(0)}{' '}
          <InformationClassBadge informationClass={d.risk.parametric_var_95.information_class} />
          <WhyDrillDown uapId={d.risk.parametric_var_95.id} portfolio={portfolio} />
        </div>
      </div>

      <div className="panel">
        <h3>Performance</h3>
        <p>
          Sharpe ratio: {d.performance.sharpe_ratio.result.toFixed(3)}{' '}
          <InformationClassBadge informationClass={d.performance.sharpe_ratio.information_class} />
        </p>
      </div>

      <div className="panel">
        <h3>
          Capital Efficiency Score {d.capital_efficiency.validation_status !== 'VERIFIED' && '(provisional — not authoritative)'}
        </h3>
        <p className="stat__value">{Math.round(d.capital_efficiency.result)} / 100</p>
        <table className="data-table">
          <tbody>
            {Object.entries(d.capital_efficiency.sub_scores).map(([name, uap]) => (
              <tr key={name}>
                <td>{name.replace(/_/g, ' ')}</td>
                <td>{Math.round(uap.result)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
