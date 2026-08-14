import { useEffect, useState } from 'react'
import type {
  AskResponse,
  EvidenceResponse,
  OpportunitiesResponse,
  PortfolioResponse,
  PortfolioVariant,
  ResearchResponse,
  RiskResponse,
  ScenarioRunResponse,
  ScenarioSummary,
  TodayResponse,
} from './types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'

class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(body.detail ?? `Request to ${path} failed (${res.status})`, res.status)
  }
  return res.json() as Promise<T>
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}))
    throw new ApiError(errorBody.detail ?? `Request to ${path} failed (${res.status})`, res.status)
  }
  return res.json() as Promise<T>
}

export const api = {
  today: (portfolio: PortfolioVariant) => get<TodayResponse>(`/today?portfolio=${portfolio}`),
  portfolio: (portfolio: PortfolioVariant) => get<PortfolioResponse>(`/portfolio?portfolio=${portfolio}`),
  opportunities: (portfolio: PortfolioVariant) =>
    get<OpportunitiesResponse>(`/opportunities?portfolio=${portfolio}`),
  risk: (portfolio: PortfolioVariant) => get<RiskResponse>(`/risk?portfolio=${portfolio}`),
  research: (assetId: string, portfolio: PortfolioVariant) =>
    get<ResearchResponse>(`/research/${encodeURIComponent(assetId)}?portfolio=${portfolio}`),
  scenarios: () => get<{ scenarios: ScenarioSummary[] }>('/scenarios'),
  runScenario: (scenarioId: string, portfolio: PortfolioVariant) =>
    post<ScenarioRunResponse>(`/scenarios/${encodeURIComponent(scenarioId)}/run?portfolio=${portfolio}`),
  ask: (text: string, sophistication: string, portfolio: PortfolioVariant) =>
    post<AskResponse>(`/ask?portfolio=${portfolio}`, { text, sophistication }),
  evidence: (uapId: string, portfolio: PortfolioVariant) =>
    get<EvidenceResponse>(`/evidence/${encodeURIComponent(uapId)}?portfolio=${portfolio}`),
}

export type ApiState<T> =
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'success'; data: T }

/** Centralises loading/error/data state so every screen gets the same
 * real, testable loading/error behaviour instead of per-screen
 * copy-paste (Phase E7 Testing section: "loading/error states"). */
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[]): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    setState({ status: 'loading' })
    fetcher()
      .then((data) => {
        if (!cancelled) setState({ status: 'success', data })
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState({ status: 'error', error: err instanceof Error ? err.message : 'Unknown error' })
        }
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return state
}
