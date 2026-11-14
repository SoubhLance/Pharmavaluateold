import React from 'react';
import type { ScreenResponse } from '../types';
import { evaluationData } from '../generated/evaluationData';

interface Props { result: ScreenResponse | null; isLoading: boolean; }

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));
const gaugeFraction = (p: number) => p <= evaluationData.thresholds.alphaCounterfeit
  ? (p / evaluationData.thresholds.alphaCounterfeit) * 0.1
  : p <= evaluationData.thresholds.alphaGenuine
    ? 0.1 + ((p - evaluationData.thresholds.alphaCounterfeit) / (evaluationData.thresholds.alphaGenuine - evaluationData.thresholds.alphaCounterfeit)) * 0.35
    : 0.45 + ((p - evaluationData.thresholds.alphaGenuine) / (1 - evaluationData.thresholds.alphaGenuine)) * 0.55;
const point = (angle: number, radius: number) => ({ x: 120 + Math.cos(angle * Math.PI / 180) * radius, y: 123 + Math.sin(angle * Math.PI / 180) * radius });
const arc = (start: number, end: number, radius: number) => {
  const a = point(start, radius); const b = point(end, radius);
  return `M ${a.x} ${a.y} A ${radius} ${radius} 0 0 1 ${b.x} ${b.y}`;
};

function PValueInstrument({ result }: { result: ScreenResponse | null }) {
  const pValue = result?.p_value ?? null;
  const fraction = pValue === null ? null : gaugeFraction(clamp(pValue, 0, 1));
  const needleAngle = fraction === null ? -90 : -90 + fraction * 180;
  const ticks = [
    { p: 0, label: '0.00' }, { p: evaluationData.thresholds.alphaCounterfeit, label: evaluationData.thresholds.alphaCounterfeit.toFixed(2) },
    { p: evaluationData.thresholds.alphaGenuine, label: evaluationData.thresholds.alphaGenuine.toFixed(2) }, { p: 1, label: '1.00' },
  ];
  return (
    <section className="instrument-panel pvalue-instrument" aria-label="Conformal p-value instrument">
      <div className="instrument-heading"><span className="instrument-icon">P</span><div><span className="eyebrow">CONFORMAL CALIBRATION</span><h3>P-value</h3></div><span className="instrument-unit">0–1 · BAND-EXPANDED</span></div>
      <div className="speedometer-wrap">
        <svg className="speedometer" viewBox="0 0 240 200" role="img" aria-label={pValue === null ? 'P-value not available' : `Conformal p-value ${pValue.toFixed(5)}`}>
          <path d={arc(180, 198, 94)} className="speed-arc counterfeit-arc" />
          <path d={arc(198, 261, 94)} className="speed-arc inconclusive-arc" />
          <path d={arc(261, 360, 94)} className="speed-arc genuine-arc" />
          <path d={arc(180, 360, 81)} className="speed-inner-track" />
          {ticks.map(({ p, label }) => {
            const angle = 180 + gaugeFraction(p) * 180;
            const from = point(angle, 101); const to = point(angle, 108); const text = point(angle, 119);
            const labelX = p === 0 ? 10 : p === 1 ? 230 : text.x;
            const anchor = p === 0 ? 'start' : p === 1 ? 'end' : 'middle';
            return <g key={label}><line x1={from.x} y1={from.y} x2={to.x} y2={to.y} className="gauge-tick"/><text x={labelX} y={text.y + 4} className="gauge-tick-label" textAnchor={anchor}>{label}</text></g>;
          })}
          {fraction !== null && <g className="gauge-needle" transform={`rotate(${needleAngle} 120 123)`}><path d="M120 123 L114 39 L126 39 Z"/><circle cx="120" cy="123" r="9"/></g>}
          {fraction === null && <circle cx="120" cy="123" r="7" className="gauge-center-muted"/>}
        </svg>
        <div className="speedometer-readout"><strong>{pValue === null ? '—' : pValue.toFixed(4)}</strong><span>CONFORMAL P-VALUE</span></div>
      </div>
      <div className={`instrument-decision ${result ? `decision-${labelToken(result.label)}` : ''}`}>
        <span className="decision-light" />{result?.label ?? 'Awaiting image analysis'}
      </div>
      <div className="gauge-scale-labels"><span>Counterfeit screen</span><span>Inconclusive</span><span>Consistent range</span></div>
      <p className="instrument-caption">Band arcs are expanded for visibility; the tick labels show the actual p-value limits. This is a calibration score, not the probability that a medicine is genuine.</p>
    </section>
  );
}

function labelToken(label: string) {
  if (label === 'Likely Genuine') return 'genuine';
  if (label === 'Likely Counterfeit') return 'counterfeit';
  if (label === 'Inconclusive') return 'inconclusive';
  if (label === 'Unknown Product') return 'unknown';
  return 'retake';
}

function AnomalyInstrument({ score }: { score: number | null }) {
  const range = evaluationData.calibrationRange;
  const low = Math.min(range.min, score ?? range.min);
  const high = Math.max(range.max, score ?? range.max);
  const span = high - low || 1;
  const bandStart = ((range.min - low) / span) * 100;
  const bandWidth = ((range.max - range.min) / span) * 100;
  const marker = score === null ? null : clamp(((score - low) / span) * 100, 0, 100);
  const context = score === null ? 'Awaiting score' : score < range.min ? 'Below genuine reference span' : score > range.max ? 'Above genuine reference span' : 'Within genuine reference span';
  return (
    <section className="instrument-panel score-instrument" aria-label="Anomaly score instrument">
      <div className="instrument-heading"><span className="instrument-icon score-icon">Σ</span><div><span className="eyebrow">PATCH MEMORY DISTANCE</span><h3>Anomaly score</h3></div><span className="instrument-unit">MODEL SCORE</span></div>
      <div className="score-readout"><strong>{score === null ? '—' : score.toFixed(2)}</strong><span>{context}</span></div>
      <div className="score-track-wrap"><div className="score-track"><div className="score-calibration-band" style={{ left: `${bandStart}%`, width: `${bandWidth}%` }} />{marker !== null && <span className="score-marker" style={{ left: `${marker}%` }} />}</div><div className="score-track-values"><span>{low.toFixed(2)}</span><span>{high.toFixed(2)}</span></div></div>
      <div className="calibration-legend"><span><i /> Genuine calibration scores</span><strong>{range.min.toFixed(2)} – {range.max.toFixed(2)}</strong><span className="calibration-count">n = {range.count}</span></div>
      <p className="instrument-caption">This score measures visual distance from the product's genuine patch memory. It does not classify the medicine by itself.</p>
    </section>
  );
}

function ScannerIllustration() {
  return <div className="scanner-empty-visual" aria-hidden="true"><div className="scanner-orbit orbit-a"/><div className="scanner-orbit orbit-b"/><div className="scanner-orbit orbit-c"/><div className="scanner-crosshair crosshair-x"/><div className="scanner-crosshair crosshair-y"/><div className="scanner-target"><span className="scan-pill"><i /><i /></span><span className="target-core"/></div><div className="scanner-sweep"/><span className="scanner-coordinate coord-one">PV · 01</span><span className="scanner-coordinate coord-two">INPUT READY</span></div>;
}

export const DiagnosticInstruments: React.FC<Props> = ({ result, isLoading }) => (
  <div className={`diagnostic-workspace ${isLoading ? 'is-scanning' : ''}`}>
    <div className="diagnostic-titlebar"><div><span className="section-index">02</span><div><span className="eyebrow">DIAGNOSTIC INTELLIGENCE</span><h2>Screening instrument</h2></div></div><span className={`diagnostic-status ${isLoading ? 'processing' : result ? 'complete' : 'standby'}`}><i />{isLoading ? 'SCREENING REQUEST IN PROGRESS' : result ? 'ANALYSIS RECEIVED' : 'SYSTEM STANDBY'}</span></div>
    {isLoading ? (
      <div className="scanner-processing" role="status" aria-live="polite"><ScannerIllustration /><div className="processing-copy"><span className="eyebrow">LOCAL INFERENCE PIPELINE</span><h3>Analyzing specimen</h3><p>The screening request is being processed. Results will appear when the backend responds.</p><div className="pipeline-ribbon"><span>Quality gate</span><i/><span>Product match</span><i/><span>Patch analysis</span><i/><span>Conformal decision</span></div><div className="indeterminate-track"><i /></div><small>Processing indicator · elapsed time depends on the device</small><div className="processing-skeletons" aria-hidden="true"><i/><i/><i/></div></div></div>
    ) : !result ? (
      <div className="scanner-empty-state"><ScannerIllustration /><div className="scanner-empty-copy"><span className="eyebrow">READY FOR SPECIMEN</span><h3>Clarity before classification.</h3><p>Load a medicine photograph to inspect capture quality, identify a reference product and review patch-level visual deviation.</p><div className="pipeline-ribbon"><span>01 Quality</span><i/><span>02 Identify</span><i/><span>03 Compare</span><i/><span>04 Calibrate</span></div><span className="empty-note">No image data is processed until you start a scan.</span></div></div>
    ) : result.label === 'Retake Required' ? (
      <div className="instrument-empty-state quality-empty"><div className="quality-empty-symbol" aria-hidden="true">↻</div><div><span className="eyebrow">CAPTURE QUALITY GATE</span><h3>Screening instruments are paused</h3><p>This result describes photograph quality only. Retake the image to continue; it is not a medicine authenticity result.</p></div></div>
    ) : (
      <div className="instrument-grid"><PValueInstrument result={result} /><AnomalyInstrument score={result.anomaly_score} /></div>
    )}
  </div>
);
