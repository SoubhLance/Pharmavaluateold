import React from 'react';
import type { ScreenHistoryItem } from '../types';

interface HistoryListProps { history: ScreenHistoryItem[]; activeId: string | null; onSelect: (item: ScreenHistoryItem) => void; }
const token = (label: string) => label === 'Likely Genuine' ? 'genuine' : label === 'Inconclusive' ? 'inconclusive' : label === 'Likely Counterfeit' ? 'counterfeit' : label === 'Unknown Product' ? 'unknown' : 'retake';

export const HistoryList: React.FC<HistoryListProps> = ({ history, activeId, onSelect }) => {
  if (!history.length) return null;
  return (
    <section className="history-section" aria-labelledby="history-heading">
      <div className="history-header"><div><span className="eyebrow">THIS SESSION</span><h2 id="history-heading">Recent scans <span>{history.length}</span></h2></div><span>Stored in memory · clears when this page reloads</span></div>
      <div className="history-scroll-container" aria-label="Recent screening results">
        {history.map((item) => <button type="button" key={item.id} className={`history-card ${item.id === activeId ? 'active' : ''}`} onClick={() => onSelect(item)} aria-current={item.id === activeId ? 'true' : undefined} aria-label={`Reopen ${item.fileName}, result ${item.result.label}`}>
          <span className="history-thumb-wrap"><img src={item.thumbnailUrl} alt="" className="history-thumb"/><span className="history-thumb-glint"/></span>
          <span className="history-info"><span className={`history-badge badge-${token(item.result.label)}`}>{item.result.label}</span><strong className="history-product" title={item.result.product_id || item.fileName}>{item.result.product_id || item.fileName}</strong><span className="history-meta"><span>p {item.result.p_value === null ? '—' : item.result.p_value.toFixed(4)}</span><i/><time dateTime={item.timestamp.toISOString()}>{item.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time></span></span>
        </button>)}
      </div>
    </section>
  );
};
