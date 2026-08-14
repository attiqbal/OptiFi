import { useState } from 'react'
import { api, useApi } from '../api/client'
import type { ScenarioRunResponse, ScenarioSummary } from '../api/types'
import { usePortfolioVariant } from '../App'
import { ConfidenceBadge } from '../components/shared/ConfidenceBadge'
import { ErrorState, LoadingState } from '../components/shared/States'

export function ScenarioLabScreen() {
  const { portfolio } = usePortfolioVariant()
  const listState = useApi<{ scenarios: ScenarioSummary[] }>(() => api.scenarios(), [])
  const [selected, setSelected] = useState<string | null>(null)
  const [result, setResult] = useState<ScenarioRunResponse | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function runScenario(id: string) {
    setSelected(id)
    setRunning(true)
    setError(null)
    setResult(null)
    try {
      setResult(await api.runScenario(id, portfolio))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run scenario.')
    } finally {
      setRunning(false)
    }
  }

  if (listState.status === 'loading') return <LoadingState label="Loading scenario library…" />
  if (listState.status === 'error') return <ErrorState message={listState.error} />

  return (
    <div>
      <h1>Scenario Lab</h1>
      <p className="muted">Explore approved, pre-vetted scenarios against your portfolio. Never a prediction — a plausible future.</p>

      <div className="scenario-picker">
        {listState.data.scenarios.map((s) => (
          <button
            key={s.scenario_id}
            type="button"
            className={`scenario-picker__button${selected === s.scenario_id ? ' scenario-picker__button--active' : ''}`}
            onClick={() => runScenario(s.scenario_id)}
          >
            {s.description}
          </button>
        ))}
      </div>

      {running && <LoadingState label="Propagating scenario…" />}
      {error && <ErrorState message={error} />}

      {result && !result.available && (
        <div className="panel">
          <p>{result.message}</p>
        </div>
      )}

      {result?.available && (
        <div className="panel">
          <h3>Scenario assumptions</h3>
          <p>
            {result.assumptions?.description} ({result.assumptions?.magnitude} {result.assumptions?.unit}, horizon{' '}
            {result.assumptions?.horizon})
          </p>

          <h3>Affected variables</h3>
          <p>{result.affected_variables?.join(', ')}</p>

          <h3>Estimated portfolio impact</h3>
          <p>Base case: {((result.portfolio_distribution?.base_case ?? 0) * 100).toFixed(2)}%</p>
          <p>
            Range: {((result.portfolio_distribution?.range_low ?? 0) * 100).toFixed(2)}% to{' '}
            {((result.portfolio_distribution?.range_high ?? 0) * 100).toFixed(2)}%
          </p>

          <h3>Winners / losers</h3>
          <p>Most positively affected: {result.winners ?? 'none identified'}</p>
          <p>Potentially negative: {result.losers ?? 'none identified'}</p>

          <h3>Uncertainties</h3>
          <ul>
            {result.uncertainties?.map((u) => (
              <li key={u} className="faint">
                {u}
              </li>
            ))}
          </ul>

          {result.confidence && <ConfidenceBadge breakdown={result.confidence} />}
        </div>
      )}
    </div>
  )
}
