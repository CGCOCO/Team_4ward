import { BrowserRouter, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import PreviewPage from './pages/PreviewPage'
import AnalyzingPage from './pages/AnalyzingPage'
import ResultPage from './pages/ResultPage'
import HistoryPage from './pages/HistoryPage'
import AdminPage from './pages/AdminPage'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import RequireAuth from './components/RequireAuth'

function Protected({ children }) {
  return <RequireAuth>{children}</RequireAuth>
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/" element={<Protected><HomePage /></Protected>} />
        <Route path="/preview" element={<Protected><PreviewPage /></Protected>} />
        <Route path="/analyzing" element={<Protected><AnalyzingPage /></Protected>} />
        <Route path="/result" element={<Protected><ResultPage /></Protected>} />
        <Route path="/history" element={<Protected><HistoryPage /></Protected>} />
        <Route path="/admin" element={<Protected><AdminPage /></Protected>} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
