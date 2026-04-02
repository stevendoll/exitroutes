import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import ThankYou from './pages/ThankYou'
import Migrate from './pages/Migrate'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/thank-you" element={<ThankYou />} />
        <Route path="/migrate" element={<Migrate />} />
      </Routes>
    </BrowserRouter>
  )
}
