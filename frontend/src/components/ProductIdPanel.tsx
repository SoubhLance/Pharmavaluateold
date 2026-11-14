import React from 'react';
import type { Top5Detail } from '../types';
import { evaluationData } from '../generated/evaluationData';

interface ProductIdPanelProps { top5Details: Top5Detail[] | null; bestSimilarity: number | null; productId: string | null; isQualityFailed: boolean; }

export const ProductIdPanel: React.FC<ProductIdPanelProps> = ({ top5Details, bestSimilarity, productId, isQualityFailed }) => {
  const tau = evaluationData.thresholds.tau;
  const bestSim = bestSimilarity ?? top5Details?.[0]?.similarity ?? null;
  const noCandidates = isQualityFailed || !top5Details?.length;
  return (
    <section className="product-id-panel">
      <div className="product-id-header"><div><span className="eyebrow">DINOv2 · COSINE RETRIEVAL</span><h3>Product identification</h3></div><span className="tau-threshold-badge">τ {tau.toFixed(4)}</span></div>
      {noCandidates ? <div className="product-empty-state"><span className="product-empty-icon" aria-hidden="true">⌕</span><div><strong>{isQualityFailed ? 'Identification not run' : 'No reference candidates returned'}</strong><p>{isQualityFailed ? 'The capture quality gate must pass before product matching.' : 'No top match data was included in the backend response.'}</p></div></div> : <>
        <div className="product-selected"><span className="selected-marker"/><div><span>SELECTED PRODUCT</span><strong>{productId && productId !== 'Unknown Product' ? productId : 'No confident product match'}</strong></div><strong className="selected-similarity">{bestSim === null ? '—' : bestSim.toFixed(4)}</strong></div>
        <div className="top5-list">{top5Details!.slice(0, 5).map((item, index) => {
          const selected = item.product_id === productId && productId !== 'Unknown Product';
          const similarity = Math.max(0, Math.min(1, item.similarity));
          return <div className={`top5-row ${selected ? 'selected' : ''}`} key={`${item.product_id}-${index}`}><div className="top5-info"><span><b>{String(index + 1).padStart(2, '0')}</b><strong>{item.product_id}</strong>{selected && <em>SELECTED</em>}</span><span>{item.similarity.toFixed(4)}</span></div><div className="top5-bar-wrapper" role="img" aria-label={`${item.product_id}, similarity ${item.similarity.toFixed(4)}, ${item.similarity >= tau ? 'at or above' : 'below'} threshold`}><span className="top5-bar-fill" style={{ width: `${similarity * 100}%` }}/><span className="tau-reference-line" style={{ left: `${tau * 100}%` }}/></div></div>;
        })}</div>
      <div className="product-scale-labels"><span>0.00</span><span className="tau-scale" style={{ left: `${tau * 100}%` }}>τ {tau.toFixed(4)}</span><span>1.00 similarity</span></div>
        {bestSim !== null && bestSim < tau && <div className="tau-warning-note">Best candidate is below τ. The product is classified as Unknown Product.</div>}
      </>}
      <p className="product-id-note">Similarity ranks catalog candidates. It is used for product identification, not counterfeit classification.</p>
    </section>
  );
};
