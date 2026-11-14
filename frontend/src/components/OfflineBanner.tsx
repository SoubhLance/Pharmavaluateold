import React from 'react';

interface OfflineBannerProps {
  onRetry: () => void;
  isRetrying: boolean;
}

export const OfflineBanner: React.FC<OfflineBannerProps> = ({ onRetry, isRetrying }) => {
  return (
    <aside
      className="offline-banner"
      role="alert"
      aria-live="assertive"
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      <span>
        Backend offline — unable to connect to screening server (http://127.0.0.1:8000). Polling every 10s.
      </span>
      <button
        type="button"
        onClick={onRetry}
        disabled={isRetrying}
      >
        {isRetrying ? 'Checking…' : 'Retry Now'}
      </button>
    </aside>
  );
};

