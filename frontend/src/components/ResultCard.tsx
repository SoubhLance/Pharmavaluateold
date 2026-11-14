import React from 'react';
import type { ScreenResponse, ScreeningLabel } from '../types';
import { CaptureQualityExplanation } from './CaptureQualityExplanation';
import { ProductIdPanel } from './ProductIdPanel';
import { DiagnosticInstruments } from './DiagnosticInstruments';
import { RawJsonViewer } from './RawJsonViewer';

interface ResultCardProps { result: ScreenResponse | null; isLoading: boolean; onUploadAnother: () => void; }

const resultToken = (label: ScreeningLabel) => {
  if (label === 'Likely Genuine') return 'genuine';
  if (label === 'Likely Counterfeit') return 'counterfeit';
  if (label === 'Inconclusive') return 'inconclusive';
  if (label === 'Unknown Product') return 'unknown';
  return 'retake';
};

const labelSummary = (label: ScreeningLabel) => {
  switch (label) {
    case 'Likely Genuine': return 'The appearance is consistent with the genuine reference distribution. This result is not a guarantee.';
    case 'Inconclusive': return 'The system cannot confidently classify this visual appearance. Manual verification is needed.';
    case 'Likely Counterfeit': return 'The anomaly score crossed the configured screening threshold. This alert needs manual verification.';
    case 'Unknown Product': return 'The system could not confidently identify the product against its reference catalog.';
    case 'Retake Required': return 'The photograph did not meet image quality requirements. This is not a medicine authenticity result.';
  }
};

export const ResultCard: React.FC<ResultCardProps> = ({ result, isLoading, onUploadAnother }) => (
  <section className="diagnostic-column" aria-live="polite">
    {result && !isLoading && <div className={`result-status-banner status-${resultToken(result.label)}`}>
      <span className="result-status-icon" aria-hidden="true">{result.label === 'Likely Genuine' ? '✓' : result.label === 'Likely Counterfeit' ? '!' : result.label === 'Inconclusive' ? '…' : result.label === 'Retake Required' ? '↻' : '⌕'}</span>
      <div><span className="eyebrow">SCREENING OUTCOME · PILL STREAM</span><h2>{result.label}</h2><p>{labelSummary(result.label)}</p></div>
      <span className="result-status-code">{result.label === 'Retake Required' ? 'QUALITY' : result.label === 'Unknown Product' ? 'IDENTITY' : 'SCREEN'}</span>
    </div>}
    <DiagnosticInstruments result={result} isLoading={isLoading} />
    {result && !isLoading && <>
      {result.label === 'Retake Required' ? (
        <CaptureQualityExplanation quality={result.quality} response={result} onUploadAnother={onUploadAnother} />
      ) : (
        <div className="result-detail-grid">
          <ProductIdPanel top5Details={result.top5_details} bestSimilarity={result.best_similarity} productId={result.product_id} isQualityFailed={!result.quality.passed} />
          <CaptureQualityExplanation quality={result.quality} response={result} onUploadAnother={onUploadAnother} />
        </div>
      )}

      <div className="result-footer-row"><span>{result.disclaimer || 'Screening aid, verify manually'} · Not for diagnostic or legal certification</span><RawJsonViewer data={result} /></div>
    </>}
  </section>
);
