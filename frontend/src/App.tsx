import { NavLink, Outlet, useOutletContext } from 'react-router-dom'
import { useState } from 'react'
import type { PortfolioVariant } from './api/types'

const TABS = [
  { to: '/', label: 'Today', end: true },
  { to: '/portfolio', label: 'Portfolio' },
  { to: '/opportunities', label: 'Opportunities' },
  { to: '/risk', label: 'Risk' },
  { to: '/research', label: 'Research' },
  { to: '/scenario-lab', label: 'Scenario Lab' },
  { to: '/ask', label: 'Ask OptiFi' },
]

export interface AppContext {
  portfolio: PortfolioVariant
  setPortfolio: (v: PortfolioVariant) => void
}

export function usePortfolioVariant() {
  return useOutletContext<AppContext>()
}

function App() {
  const [portfolio, setPortfolio] = useState<PortfolioVariant>('default')

  return (
    <div className="app-shell">
      <nav className="app-nav" aria-label="Primary">
        <div className="app-nav__brand">OptiFi</div>
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) => `app-nav__link${isActive ? ' app-nav__link--active' : ''}`}
          >
            {tab.label}
          </NavLink>
        ))}
        <div style={{ marginTop: 'auto', padding: '1rem 1.5rem' }}>
          <label htmlFor="portfolio-variant" className="faint" style={{ display: 'block', marginBottom: '0.25rem' }}>
            Demo portfolio
          </label>
          <select
            id="portfolio-variant"
            value={portfolio}
            onChange={(e) => setPortfolio(e.target.value as PortfolioVariant)}
            style={{ width: '100%' }}
          >
            <option value="default">Default (has opportunities)</option>
            <option value="efficient">Efficient (no opportunities)</option>
          </select>
        </div>
      </nav>
      <main className="app-main">
        <Outlet context={{ portfolio, setPortfolio } satisfies AppContext} />
      </main>
    </div>
  )
}

export default App
