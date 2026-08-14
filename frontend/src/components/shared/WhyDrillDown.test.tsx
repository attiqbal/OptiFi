import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { WhyDrillDown } from './WhyDrillDown'
import type { UAP } from '../../api/types'

vi.mock('../../api/client', () => ({
  api: {
    evidence: vi.fn(),
  },
}))

const ROOT: UAP = {
  id: 'root-1',
  subject: 'root judgement',
  information_class: 'JUDGEMENT',
  validation_status: 'PROVISIONAL',
  result: {},
  source: 's',
  producer: 'ai-engine',
  generated_at: '2026-01-01T00:00:00Z',
  confidence: 'MODERATE',
  assumptions: [],
  limitations: [],
  dependencies: ['fact-1'],
  provenance_chain: ['fact-1'],
  disagreement_set_ref: null,
}

const FACT: UAP = {
  ...ROOT,
  id: 'fact-1',
  subject: 'underlying fact',
  information_class: 'FACT',
  validation_status: 'VERIFIED',
  producer: 'data-engine',
  dependencies: [],
  provenance_chain: [],
}

describe('WhyDrillDown', () => {
  it('lazily fetches and renders the real evidence chain on open, labelling each step by producer and information_class', async () => {
    const { api } = await import('../../api/client')
    vi.mocked(api.evidence).mockResolvedValue({ root_id: ROOT.id, chain: [ROOT, FACT] })

    render(<WhyDrillDown uapId={ROOT.id} portfolio="default" />)
    expect(api.evidence).not.toHaveBeenCalled()

    await userEvent.click(screen.getByText('Why?'))

    await waitFor(() => expect(screen.getByText('underlying fact')).toBeInTheDocument())
    expect(screen.getByText('root judgement')).toBeInTheDocument()
    expect(screen.getByText('data-engine')).toBeInTheDocument()
    expect(screen.getByText('ai-engine')).toBeInTheDocument()
  })
})
