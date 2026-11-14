import React, { useState } from 'react';
import type { ScreenResponse } from '../types';

interface RawJsonViewerProps {
  data: ScreenResponse | null;
}

export const RawJsonViewer: React.FC<RawJsonViewerProps> = ({ data }) => {
  const [copied, setCopied] = useState(false);

  if (!data) return null;

  const jsonString = JSON.stringify(data, null, 2);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(jsonString);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy json', err);
    }
  };

  return (
    <details className="raw-json-details">
      <summary className="raw-json-summary">
        <span>Raw API Response (JSON)</span>
        <button
          type="button"
          className="btn-copy"
          onClick={handleCopy}
          aria-label="Copy raw JSON response to clipboard"
        >
          {copied ? (
            <>
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span>Copied!</span>
            </>
          ) : (
            <>
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              <span>Copy JSON</span>
            </>
          )}
        </button>
      </summary>
      <div className="raw-json-body">
        <pre className="raw-json-code">
          <code>{jsonString}</code>
        </pre>
      </div>
    </details>
  );
};

