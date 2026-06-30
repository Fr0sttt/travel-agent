import { Routes, Route } from 'react-router'
import { TravelProvider } from './contexts/TravelContext'
import Layout from './components/Layout'
import Home from './pages/Home'
import AppDashboard from './pages/AppDashboard'
import Preferences from './pages/Preferences'
import Security from './pages/Security'

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
        <Route path="/preferences" element={<Preferences />} />
        <Route path="/security" element={<Security />} />
      </Routes>
    </Layout>
  )
}
