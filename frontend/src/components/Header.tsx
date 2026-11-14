import React from 'react';
import type { HealthResponse } from '../types';

interface HeaderProps {
  activeTab: 'screen' | 'about';
  setActiveTab: (tab: 'screen' | 'about') => void;
  health: HealthResponse | null;
  isOnline: boolean;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab, health, isOnline }) => {
  const device = health?.device ?? '';
  const gpuAvailable = /cuda|gpu/i.test(device);
  return (
    <>
      <div className="safety-strip">
        <span className="safety-mark" aria-hidden="true">+</span>
        <span>Research screening aid only</span>
        <span className="safety-divider" />
        <span>Always verify with a qualified professional</span>
      </div>
      <header className="site-header">
        <a className="brand-lockup" href="#screening" onClick={(event) => { event.preventDefault(); setActiveTab('screen'); }} aria-label="PharmaValuate screening home">
          <span className="brand-symbol" aria-hidden="true"><svg viewBox="0 0 44 44" fill="none"><rect x="4" y="4" width="36" height="36" rx="12" fill="currentColor"/><path d="M15 22h14M22 15v14" stroke="white" strokeWidth="2.8" strokeLinecap="round"/><path d="M31 11a13 13 0 0 1 2.5 19" stroke="white" strokeOpacity=".55" strokeWidth="1.6" strokeLinecap="round"/></svg></span>
          <span className="brand-wordmark"><strong>PharmaValuate</strong><span>MEDICINE IMAGE SCREENING</span></span>
          <span className="stream-mark"><i aria-hidden="true" /> PILL STREAM</span>
        </a>

        <nav className="main-nav" aria-label="Main navigation">
          <button type="button" className={activeTab === 'screen' ? 'active' : ''} onClick={() => setActiveTab('screen')} aria-current={activeTab === 'screen' ? 'page' : undefined}>Screening</button>
          <button type="button" className={activeTab === 'about' ? 'active' : ''} onClick={() => setActiveTab('about')} aria-current={activeTab === 'about' ? 'page' : undefined}>Method &amp; Evaluation</button>
        </nav>

        <div className="header-statuses">
          <div className={`system-status ${isOnline ? 'online' : 'offline'}`} title={isOnline ? `Backend device: ${device || 'initializing'}` : 'Screening backend is unavailable'}>
            <span className="status-pulse" aria-hidden="true" />
            <span>{isOnline ? 'Backend online' : 'Backend offline'}</span>
          </div>
          <div className={`gpu-status ${gpuAvailable ? 'available' : ''}`} title={isOnline ? `Device reported by backend: ${device || 'not reported'}` : 'Device information unavailable'}>
            <svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><rect x="3" y="4" width="14" height="12" rx="2" stroke="currentColor" strokeWidth="1.5"/><path d="M7 8h6v4H7zM1 7v6m18-6v6M7 2v2m6-2v2m-6 12v2m6-2v2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
            <span>{isOnline ? gpuAvailable ? 'CUDA ready' : device || 'Device ready' : 'GPU status unavailable'}</span>
          </div>
          <span className="theme-indicator"><span aria-hidden="true">☼</span> Light</span>
        </div>
      </header>
    </>
  );
};
