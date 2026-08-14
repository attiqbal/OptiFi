import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { AskOptiFiScreen } from './screens/AskOptiFiScreen.tsx'
import { OpportunitiesScreen } from './screens/OpportunitiesScreen.tsx'
import { PortfolioScreen } from './screens/PortfolioScreen.tsx'
import { ResearchScreen } from './screens/ResearchScreen.tsx'
import { RiskScreen } from './screens/RiskScreen.tsx'
import { ScenarioLabScreen } from './screens/ScenarioLabScreen.tsx'
import { TodayScreen } from './screens/TodayScreen.tsx'

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <TodayScreen /> },
      { path: 'portfolio', element: <PortfolioScreen /> },
      { path: 'opportunities', element: <OpportunitiesScreen /> },
      { path: 'risk', element: <RiskScreen /> },
      { path: 'research', element: <ResearchScreen /> },
      { path: 'research/:assetId', element: <ResearchScreen /> },
      { path: 'scenario-lab', element: <ScenarioLabScreen /> },
      { path: 'ask', element: <AskOptiFiScreen /> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
