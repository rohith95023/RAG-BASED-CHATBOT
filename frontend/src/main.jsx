import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './animations.css'
import './typing.css'
import App from './App.jsx'
import { AuthProvider } from './contexts/AuthContext.jsx'

if ('speechSynthesis' in window) {
  window.speechSynthesis.cancel();
}

// Ensure root element has proper sizing
const rootElement = document.getElementById('root')
if (rootElement) {
  rootElement.style.width = '100%'
  rootElement.style.height = '100%'
  rootElement.style.overflow = 'hidden'
}

// Handle window resize to update mobile menu toggle visibility
const handleResize = () => {
  const mobileToggle = document.querySelector('.mobile-menu-toggle')
  if (mobileToggle) {
    mobileToggle.style.display = window.innerWidth <= 768 ? 'flex' : 'none'
  }
}

window.addEventListener('resize', handleResize)
handleResize() // Initial check

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>,
)
