import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EmptyState, ErrorState, LoadingState } from './States'

describe('States', () => {
  it('LoadingState announces politely for screen readers', () => {
    render(<LoadingState label="Loading portfolio…" />)
    const el = screen.getByRole('status')
    expect(el).toHaveTextContent('Loading portfolio…')
  })

  it('ErrorState is announced as an alert', () => {
    render(<ErrorState message="network down" />)
    expect(screen.getByRole('alert')).toHaveTextContent('network down')
  })

  it('EmptyState renders the real "no opportunities" copy, not a generic placeholder', () => {
    render(<EmptyState message="No new opportunities today. Your capital allocation remains efficient against your current mandate." />)
    expect(screen.getByText(/No new opportunities today/)).toBeInTheDocument()
  })
})
