import { Routes, Route } from 'react-router'
import { TravelProvider } from './contexts/TravelContext'
import Layout from './components/Layout'
import Home from './pages/Home'
import AppDashboard from './pages/AppDashboard'
import Preferences from './pages/Preferences'
import Security from './pages/Security'
import HowItWorks from './pages/HowItWorks'
import EvaluationReport from './pages/EvaluationReport'
import TraceReport from './pages/TraceReport'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/app" element={
          <TravelProvider>
            <AppDashboard />
          </TravelProvider>
        } />
        <Route path="/evaluation" element={<EvaluationReport />} />
        <Route path="/trace" element={<TraceReport />} />
        <Route path="/preferences" element={<Preferences />} />
        <Route path="/security" element={<Security />} />
        <Route path="/how-it-works" element={<HowItWorks />} />
      </Routes>
    </Layout>
  )
}
