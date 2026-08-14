import { api, useApi } from '../api/client'
import type { RiskResponse } from '../api/types'
import { usePortfolioVariant } from '../App'
import { InformationClassBadge } from '../components/shared/InformationClassBadge'
import { ErrorState, LoadingState } from '../components/shared/States'
import { WhyDrillDown } from '../components/shared/WhyDrillDown'

export function RiskScreen() {
  const { portfolio } = usePortfolioVariant()
  const state = useApi<RiskResponse>(() => api.risk(portfolio), [portfolio])

  if (state.status === 'loading') return <LoadingState label="Loading risk analysis…" />
  if (state.status === 'error') return <ErrorState message={state.error} />
  const d = state.data

  return (
    <div>
      <h1>Risk</h1>

      <div className="panel">
        <h3>Major risk contributors</h3>
        <table className="data-table">
          <tbody>
            {Object.entries(d.risk_contributors.result as Record<string, number>).map(([entity, share]) => (
              <tr key={entity}>
                <td>{entity}</td>
                <td>{(share * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
        <InformationClassBadge informationClass={d.risk_contributors.information_class} />
        <WhyDrillDown uapId={d.risk_contributors.id} portfolio={portfolio} />
      </div>

      <div className="panel panel-grid">
        <div className="stat">
          <span className="stat__label">Largest holding</span>
          <span className="stat__value">{(d.concentration.largest_weight * 100).toFixed(1)}%</span>
          <span className="faint">{d.concentration.largest_holding}</span>
        </div>
        <div className="stat">
          <span className="stat__label">Portfolio std. dev (monthly)</span>
          <span className="stat__value">{(d.volatility.portfolio_std_dev * 100).toFixed(2)}%</span>
        </div>
        <div className="stat">
          <span className="stat__label">Duration (illustrative)</span>
          <span className="stat__value">{d.duration.result}</span>
        </div>
      </div>

      <div className="panel">
        <h3>Drawdown scenarios</h3>
        <p>
          Historical VaR (95%, monthly return): {(d.drawdown_scenarios.historical_var_95.result * 100).toFixed(2)}%{' '}
          <InformationClassBadge informationClass="ESTIMATE" />
        </p>
        <p>Parametric VaR (95%): £{d.drawdown_scenarios.parametric_var_95.result.toFixed(0)}</p>
        <p className="faint">
          Rate-cut scenario (illustrative), rate-sensitive holdings only: base case{' '}
          {((d.drawdown_scenarios.rate_cut_scenario.result.portfolio_base_case as number) * 100).toFixed(2)}%
        </p>
      </div>

      <div className="panel">
        <h3>FX exposure</h3>
        {Object.keys(d.fx_exposure).length === 0 ? (
          <p className="muted">No non-GBP exposure.</p>
        ) : (
          <table className="data-table">
            <tbody>
              {Object.entries(d.fx_exposure).map(([ccy, share]) => (
                <tr key={ccy}>
                  <td>{ccy}</td>
                  <td>{(share * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel">
        <h3>Scenario sensitivity — "UK base rate: -100bp"</h3>
        {Object.entries(d.scenario_sensitivity).map(([entity, uap]) => (
          <div key={entity} className="card">
            <h3>{entity}</h3>
            <p>{uap.result}</p>
            <InformationClassBadge informationClass={uap.information_class} />
            <WhyDrillDown uapId={uap.id} portfolio={portfolio} />
          </div>
        ))}
      </div>
    </div>
  )
}
