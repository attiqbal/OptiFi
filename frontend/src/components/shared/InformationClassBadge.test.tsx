import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { InformationClassBadge } from './InformationClassBadge'
import type { InformationClass } from '../../api/types'

describe('InformationClassBadge', () => {
  it.each<InformationClass>(['FACT', 'ESTIMATE', 'JUDGEMENT'])('renders %s distinctly', (cls) => {
    render(<InformationClassBadge informationClass={cls} />)
    const badge = screen.getByText(cls)
    expect(badge.className).toContain(`badge--${cls.toLowerCase()}`)
  })

  it('gives each class a different class name (not colour alone)', () => {
    const { container: fact } = render(<InformationClassBadge informationClass="FACT" />)
    const { container: estimate } = render(<InformationClassBadge informationClass="ESTIMATE" />)
    expect(fact.querySelector('.badge')?.className).not.toBe(estimate.querySelector('.badge')?.className)
  })
})
