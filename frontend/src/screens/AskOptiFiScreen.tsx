import { useState } from 'react'
import { api } from '../api/client'
import type { AskResponse, UAP } from '../api/types'
import { usePortfolioVariant } from '../App'
import { InformationClassBadge } from '../components/shared/InformationClassBadge'
import { ErrorState, LoadingState } from '../components/shared/States'
import { ValidationStatusFlag } from '../components/shared/ValidationStatusFlag'
import { WhyDrillDown } from '../components/shared/WhyDrillDown'

interface Exchange {
  question: string
  response: AskResponse
}

function UapList({ title, uaps, portfolio }: { title: string; uaps: UAP[]; portfolio: ReturnType<typeof usePortfolioVariant>['portfolio'] }) {
  if (uaps.length === 0) return null
  return (
    <div>
      <h4>{title}</h4>
      {uaps.map((u) => (
        <div key={u.id}>
          <InformationClassBadge informationClass={u.information_class} /> <ValidationStatusFlag status={u.validation_status} />{' '}
          {u.subject}
          <WhyDrillDown uapId={u.id} portfolio={portfolio} />
        </div>
      ))}
    </div>
  )
}

export function AskOptiFiScreen() {
  const { portfolio } = usePortfolioVariant()
  const [text, setText] = useState('')
  const [sophistication, setSophistication] = useState('INFORMED')
  const [exchanges, setExchanges] = useState<Exchange[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!text.trim()) return
    setLoading(true)
    setError(null)
    try {
      const response = await api.ask(text, sophistication, portfolio)
      setExchanges((prev) => [...prev, { question: text, response }])
      setText('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not reach OptiFi.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>Ask OptiFi</h1>
      <p className="muted">
        Try: "What is my technology allocation?", "What is the outlook?", or "Should I rebalance because recession risk has
        increased?"
      </p>

      <div className="ask-thread">
        {exchanges.map((ex, i) => (
          <div className="card" key={i}>
            <p>
              <strong>You:</strong> {ex.question}
            </p>
            <p className="faint">Routed to: {ex.response.routing.engines.join(', ')}</p>

            <UapList title="Facts" uaps={ex.response.facts} portfolio={portfolio} />
            <UapList title="Estimates" uaps={ex.response.estimates} portfolio={portfolio} />
            <UapList title="Judgements" uaps={ex.response.judgements} portfolio={portfolio} />

            {ex.response.disagreement_notes.length > 0 && (
              <div>
                <h4>What could change the conclusion</h4>
                {ex.response.disagreement_notes.map((n) => (
                  <p key={n} className="faint">
                    {n}
                  </p>
                ))}
              </div>
            )}

            {ex.response.roadblocks.length > 0 && (
              <div>
                <h4>Roadblocks</h4>
                {ex.response.roadblocks.map((r) => (
                  <p key={r.description} className="faint">
                    {r.description}
                  </p>
                ))}
              </div>
            )}

            {/* CIOExplanation's suggested_action is free text (ai-engine/explanation.py),
                not the fixed Today/Opportunities vocabulary — rendered as prose, not a
                pill. Directive language ("Buy X") is already redacted server-side. */}
            <p>
              <strong>Suggested action:</strong> {ex.response.suggested_action}
            </p>
          </div>
        ))}
      </div>

      {loading && <LoadingState label="OptiFi is thinking…" />}
      {error && <ErrorState message={error} />}

      <form className="ask-form" onSubmit={submit}>
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Ask OptiFi about your portfolio…"
          aria-label="Ask OptiFi"
        />
        <select value={sophistication} onChange={(e) => setSophistication(e.target.value)} aria-label="Explanation depth">
          <option value="BEGINNER">Beginner</option>
          <option value="INFORMED">Informed investor</option>
          <option value="PROFESSIONAL">Professional</option>
        </select>
        <button type="submit">Ask</button>
      </form>
    </div>
  )
}
