import React from 'react';

interface PValueBarProps {
  pValue: number | null;
}

export const PValueBar: React.FC<PValueBarProps> = ({ pValue }) => {
  if (pValue === null || pValue === undefined) {
    return null;
  }

  // Calculate percentage position along segmented bar:
  // Band 1: [0, 0.01] -> 18% visual width
  // Band 2: (0.01, 0.50] -> 41% visual width
  // Band 3: (0.50, 1.00] -> 41% visual width
  const clampedP = Math.max(0, Math.min(1, pValue));
  let markerPercent = 0;

  if (clampedP <= 0.01) {
    markerPercent = (clampedP / 0.01) * 18;
  } else if (clampedP <= 0.50) {
    markerPercent = 18 + ((clampedP - 0.01) / (0.50 - 0.01)) * 41;
  } else {
    markerPercent = 59 + ((clampedP - 0.50) / (1.00 - 0.50)) * 41;
  }

  // Keep marker within visible track bounds
  markerPercent = Math.max(1, Math.min(99, markerPercent));

  return (
    <div className="pvalue-bar-container" aria-label="Conformal p-value decision bands">
      <div className="pvalue-bar-header">
        <h4 className="pvalue-bar-title">Conformal P-Value Decision Bands</h4>
        <span className="pvalue-value-badge">p = {pValue.toFixed(5)}</span>
      </div>

      <div className="band-bar-track">
        {/* Dynamic position pin */}
        <div
          className="pvalue-marker"
          style={{ left: `${markerPercent}%` }}
          aria-label={`Current p-value ${pValue.toFixed(5)}`}
        >
          <div className="pvalue-marker-pill">p = {pValue.toFixed(4)}</div>
          <div className="pvalue-marker-pin" />
        </div>

        {/* Counterfeit Band */}
        <div
          className="band-segment counterfeit"
          title="p ≤ 0.01: Likely Counterfeit band"
        />

        {/* Inconclusive Band */}
        <div
          className="band-segment inconclusive"
          title="0.01 < p ≤ 0.50: Inconclusive band"
        />

        {/* Likely Genuine Band */}
        <div
          className="band-segment genuine"
          title="p > 0.50: Likely Genuine band"
        />
      </div>

      <div className="band-legend">
        <div className="legend-item">
          <span className="legend-color" style={{ background: 'var(--counterfeit-text)' }} />
          <span>Likely Counterfeit (p &le; 0.01)</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#f59e0b' }} />
          <span>Inconclusive (0.01 &lt; p &le; 0.50)</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#10b981' }} />
          <span>Likely Genuine (p &gt; 0.50)</span>
        </div>
      </div>
    </div>
  );
};

