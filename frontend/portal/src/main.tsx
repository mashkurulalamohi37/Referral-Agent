import React from 'react';
import ReactDOM from 'react-dom/client';
import './i18n';
import { applyColorScheme } from './lib/theme';
import App from './App';
import './styles/app.css';

// Apply the saved light/dark preference before first paint to avoid a flash.
applyColorScheme();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
