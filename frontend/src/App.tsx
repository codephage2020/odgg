// ODGG — Router shell for dual UIs (wizard + brief editor)
import { Routes, Route, Navigate } from 'react-router-dom';
import { WizardPage } from './pages/WizardPage';
import { BriefList } from './pages/BriefList';
import { BriefEditor } from './pages/BriefEditor';
import './App.css';

function App() {
  return (
    <Routes>
      {/* Brief Editor (new default) */}
      <Route path="/brief" element={<BriefList />} />
      <Route path="/brief/:briefId" element={<BriefEditor />} />

      {/* Wizard (original 8-step flow) */}
      <Route path="/wizard" element={<WizardPage />} />

      {/* Default: redirect to brief list */}
      <Route path="*" element={<Navigate to="/brief" replace />} />
    </Routes>
  );
}

export default App;
