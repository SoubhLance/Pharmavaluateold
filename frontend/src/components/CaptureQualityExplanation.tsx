import React from 'react';
import type { QualityDetails, ScreenResponse } from '../types';

interface CaptureQualityExplanationProps {
  quality: QualityDetails;
  response: ScreenResponse;
  onUploadAnother: () => void;
}

type MetricKey = 'mean_lum' | 'blur' | 'glare' | 'dark';
type MetricState = 'failed' | 'passed' | 'unknown' | 'diagnostic';

interface MetricExplanation {
  key: MetricKey;
  name: string;
  simpleName: string;
  meaning: string;
  value?: number;
  formattedValue: string;
  expected?: string;
  limitValues?: number[];
  state: MetricState;
  title?: string;
  explanation: string;
  recommendations: string[];
  shortReason: string;
}

const numberText = (value: number | undefined, digits = 2) =>
  typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : null;

const pctText = (value: number | undefined) => {
  const text = numberText(value === undefined ? undefined : value * 100);
  return text === null ? null : `${text}%`;
};

function describeMetrics(quality: QualityDetails): MetricExplanation[] {
  const thresholds = quality.thresholds;
  const lum = quality.mean_lum;
  const lumMin = thresholds?.lum_min;
  const lumMax = thresholds?.lum_max;
  const blur = quality.blur;
  const blurMin = thresholds?.blur_min;
  const glare = quality.glare;
  const glareMax = thresholds?.glare_max;
  const dark = quality.dark;

  const lumLow = lum !== undefined && lumMin !== undefined && lum < lumMin;
  const lumHigh = lum !== undefined && lumMax !== undefined && lum > lumMax;
  const lumKnown = lum !== undefined && lumMin !== undefined && lumMax !== undefined;
  const blurKnown = blur !== undefined && blurMin !== undefined;
  const glareKnown = glare !== undefined && glareMax !== undefined;
  const lumState: MetricState = lumKnown ? (lumLow || lumHigh ? 'failed' : 'passed') : 'unknown';
  const blurState: MetricState = blurKnown ? (blur < blurMin ? 'failed' : 'passed') : 'unknown';
  const glareState: MetricState = glareKnown ? (glare > glareMax ? 'failed' : 'passed') : 'unknown';

  return [
    {
      key: 'mean_lum', name: 'Mean Luminance', simpleName: 'Brightness',
      meaning: 'Measures the average brightness of the photograph.', value: lum,
      formattedValue: numberText(lum, 1) ?? 'Not provided',
      expected: lumMin !== undefined && lumMax !== undefined ? `${lumMin.toFixed(1)}–${lumMax.toFixed(1)}` : undefined,
      limitValues: lumMin !== undefined && lumMax !== undefined ? [lumMin, lumMax] : undefined,
      state: lumState,
      title: lumLow ? 'Your image is too dark' : lumHigh ? 'Your image is too bright' : undefined,
      explanation: lumLow
        ? 'The photograph does not have enough brightness for reliable medicine screening. Some details on the capsule may be difficult to distinguish.'
        : lumHigh
          ? 'The photograph is excessively bright. Strong lighting may wash out important details such as the capsule colour and printed identification.'
          : lumKnown
            ? 'The image brightness is within the range required for reliable screening.'
            : 'Brightness or its acceptable range was not included in the quality response, so this check cannot be explained more specifically.',
      recommendations: lumLow
        ? ['Move to a brighter location.', 'Use natural daylight or evenly distributed room lighting.', 'Avoid dark environments and keep the medicine clearly visible.']
        : lumHigh
          ? ['Reduce direct lighting.', 'Avoid placing the medicine directly under a strong light source.', 'Move to softer, evenly distributed lighting.']
          : [],
      shortReason: lumLow ? 'The image is darker than the required range.' : lumHigh ? 'The image is brighter than the required range.' : 'Brightness is within the required range.',
    },
    {
      key: 'blur', name: 'Sharpness (Blur)', simpleName: 'Sharpness',
      meaning: 'Measures how clearly the medicine appears in the photograph.', value: blur,
      formattedValue: numberText(blur) ?? 'Not provided',
      expected: blurMin !== undefined ? `≥ ${blurMin.toFixed(2)}` : undefined,
      limitValues: blurMin !== undefined ? [blurMin] : undefined,
      state: blurState, title: blurState === 'failed' ? 'Your image is blurry' : undefined,
      explanation: blurState === 'failed'
        ? 'The medicine is not sufficiently clear in the photograph. Fine details, including printed markings and capsule boundaries, may be difficult to inspect.'
        : blurKnown
          ? 'The medicine appears clear enough for this sharpness check.'
          : 'Sharpness or its acceptable threshold was not included in the quality response, so this check cannot be explained more specifically.',
      recommendations: blurState === 'failed' ? ['Hold your phone steady.', 'Tap the medicine on your screen to focus.', 'Avoid moving while taking the photograph and ensure the medicine is in focus.'] : [],
      shortReason: blurState === 'failed' ? 'Sharpness is below the minimum required value.' : 'Sharpness meets the required minimum.',
    },
    {
      key: 'glare', name: 'Glare Fraction', simpleName: 'Light reflections',
      meaning: 'Measures how much of the image is affected by unwanted reflections or bright spots.', value: glare,
      formattedValue: pctText(glare) ?? 'Not provided',
      expected: glareMax !== undefined ? `≤ ${pctText(glareMax)}` : undefined,
      limitValues: glareMax !== undefined ? [glareMax] : undefined,
      state: glareState, title: glareState === 'failed' ? 'Too much light reflection' : undefined,
      explanation: glareState === 'failed'
        ? "Reflections are covering parts of the medicine photograph. This can hide the capsule's colour, printed markings or surface details."
        : glareKnown
          ? 'No excessive light reflections were detected by this check.'
          : 'Glare or its permitted threshold was not included in the quality response, so this check cannot be explained more specifically.',
      recommendations: glareState === 'failed' ? ['Avoid direct flash.', 'Change the camera angle slightly.', 'Use softer lighting and a non-reflective surface.'] : [],
      shortReason: glareState === 'failed' ? 'Reflections exceed the permitted limit.' : 'Reflections are within the permitted limit.',
    },
    {
      key: 'dark', name: 'Dark Pixel Fraction', simpleName: 'Dark areas',
      meaning: 'Measures the proportion of very dark pixels in the photograph.', value: dark,
      formattedValue: pctText(dark) ?? 'Not provided', expected: undefined,
      state: 'diagnostic',
      explanation: 'This is a diagnostic measurement. The backend does not use it as a separate pass/fail condition for the capture quality gate.',
      recommendations: [], shortReason: 'Diagnostic only; no separate rejection threshold is returned by the backend.',
    },
  ];
}

function primaryHeading(failed: MetricExplanation[]) {
  if (failed.length > 1 && failed.some((metric) => metric.key === 'glare') && failed.some((metric) => metric.key === 'mean_lum')) {
    return 'Your photo needs better lighting';
  }
  return failed[0]?.title ?? (failed.length > 1 ? 'Several photo quality checks need attention' : 'This photo needs a quality adjustment');
}

export const CaptureQualityExplanation: React.FC<CaptureQualityExplanationProps> = ({ quality, response, onUploadAnother }) => {
  const metrics = describeMetrics(quality);
  const failed = metrics.filter((metric) => metric.state === 'failed');

  if (quality.passed) {
    return (
      <section className="capture-quality" aria-labelledby="capture-quality-title">
        <div className="capture-quality-success">
          <span className="capture-quality-icon success-icon" aria-hidden="true">✓</span>
          <div><h3 id="capture-quality-title">Image quality looks good</h3><p>Your photograph passed the capture quality checks and is ready for further analysis.</p></div>
        </div>
        <div className="capture-metric-grid compact">
          {metrics.map((metric) => <MetricCard key={metric.key} metric={metric} />)}
        </div>
        <TechnicalDetails metrics={metrics} response={response} />
      </section>
    );
  }

  return (
    <section className="capture-quality" aria-labelledby="capture-quality-title">
      <div className="retake-heading">
        <span className="capture-quality-icon warning-icon" aria-hidden="true">!</span>
        <div><h3 id="capture-quality-title">Retake Required</h3><p>We couldn't analyse this photograph reliably because some image quality requirements were not met.</p></div>
      </div>

      <div className="primary-quality-issue">
        <div className="quality-issue-eyebrow">{failed.length > 1 ? `${failed.length} image quality issues found` : 'Main image quality issue'}</div>
        <h4>{primaryHeading(failed)}</h4>
        {failed.length === 0 ? (
          <p>The backend marked the capture quality gate as failed but did not provide enough metric values and thresholds to identify a specific cause. Try a clear photo with even lighting.</p>
        ) : failed.length >= 3 ? (
          <p>{failed.length} photo checks did not meet their requirements. Open the details below to see each issue and how to address it.</p>
        ) : (
          <div className="primary-issue-list">
            {failed.map((metric) => <div key={metric.key} className="primary-issue-item"><strong>{metric.title ?? metric.name}</strong><p>{metric.explanation}</p><p className="capture-reading">Measured {metric.formattedValue}; expected {metric.expected ?? 'threshold not provided'}.</p><Recommendation metric={metric} prominent /></div>)}
          </div>
        )}
      </div>

      {failed.length >= 3 ? (
        <details className="capture-technical-details">
          <summary>View detailed quality report and recommendations</summary>
          <div className="capture-metric-grid">
            {metrics.map((metric) => <MetricCard key={metric.key} metric={metric} />)}
          </div>
        </details>
      ) : (
        <>
          <h4 className="quality-section-title">Detailed quality report</h4>
          <div className="capture-metric-grid">
            {metrics.map((metric) => <MetricCard key={metric.key} metric={metric} />)}
          </div>
        </>
      )}

      <div className="retake-guide">
        <h4>How to take a better medicine photo</h4>
        <ol>
          <li><span aria-hidden="true">▧</span><span>Place the capsule on a clean, plain surface.</span></li>
          <li><span aria-hidden="true">☼</span><span>Use bright, evenly distributed lighting.</span></li>
          <li><span aria-hidden="true">◎</span><span>Hold the camera steady and focus on the capsule.</span></li>
          <li><span aria-hidden="true">◉</span><span>Avoid reflections and harsh shadows.</span></li>
        </ol>
        <button type="button" className="btn-primary upload-another-button" onClick={onUploadAnother}>Upload Another Image</button>
      </div>

      <TechnicalDetails metrics={metrics} response={response} />
    </section>
  );
};

const Recommendation: React.FC<{ metric: MetricExplanation; prominent?: boolean }> = ({ metric, prominent = false }) => {
  if (metric.recommendations.length === 0) return null;
  return <div className={prominent ? 'issue-recommendation prominent' : 'issue-recommendation'}><strong>What to do</strong><ul>{metric.recommendations.map((item) => <li key={item}>{item}</li>)}</ul></div>;
};

const MetricCard: React.FC<{ metric: MetricExplanation }> = ({ metric }) => {
  const statusLabel = metric.state === 'failed' ? 'FAIL' : metric.state === 'passed' ? 'PASS' : metric.state === 'diagnostic' ? 'NORMAL' : 'UNKNOWN';
  return (
    <article className={`capture-metric-card ${metric.state}`}>
      <div className="capture-metric-heading"><h5>{metric.name}</h5><span className={`capture-status ${metric.state}`}>{statusLabel}</span></div>
      <p className="capture-metric-meaning">{metric.meaning}</p>
      <MetricTrack metric={metric} />
      <div className="capture-metric-facts"><div className="metric-measured"><span>Measured</span><strong>{metric.formattedValue}</strong></div><div className="metric-expected"><span>Expected</span><strong>{metric.expected ?? 'Not specified'}</strong></div></div>
      <p className="capture-metric-explanation">{metric.state === 'failed' ? metric.shortReason : metric.explanation}</p>
      {metric.state === 'failed' && <Recommendation metric={metric} />}
    </article>
  );
};

const MetricTrack: React.FC<{ metric: MetricExplanation }> = ({ metric }) => {
  if (metric.value === undefined || !Number.isFinite(metric.value)) return null;
  const validLimits = metric.limitValues ?? [];
  const ceiling = metric.key === 'dark' ? 1 : Math.max(metric.value, ...validLimits, metric.key === 'glare' ? 0.005 : 0.01) * 1.12;
  const position = Math.max(0, Math.min(100, (metric.value / ceiling) * 100));
  const limitStart = metric.key === 'mean_lum' && validLimits.length === 2 ? (validLimits[0] / ceiling) * 100 : undefined;
  const limitEnd = metric.key === 'mean_lum' && validLimits.length === 2 ? (validLimits[1] / ceiling) * 100 : validLimits[0] !== undefined ? (validLimits[0] / ceiling) * 100 : undefined;
  return <div className={`metric-track ${metric.state}`} aria-label={`${metric.name} visual measurement`}><span className="metric-track-fill" style={{ width: `${position}%` }} />{limitStart !== undefined && limitEnd !== undefined ? <span className="metric-track-range" style={{ left: `${limitStart}%`, width: `${Math.max(0, limitEnd - limitStart)}%` }} /> : null}{limitEnd !== undefined && <span className="metric-track-limit" style={{ left: `${limitEnd}%` }} />}</div>;
};

const TechnicalDetails: React.FC<{ metrics: MetricExplanation[]; response: ScreenResponse }> = ({ metrics, response }) => (
  <details className="capture-technical-details">
    <summary>View Technical Details</summary>
    <div className="technical-metrics-list">{metrics.map((metric) => <div key={metric.key}><span>{metric.name}</span><code>{metric.formattedValue}</code><span>{metric.expected ? `Expected ${metric.expected}` : metric.key === 'dark' ? 'No backend threshold supplied' : 'Threshold unavailable'}</span><span>{metric.state === 'failed' ? 'Failed' : metric.state === 'passed' ? 'Passed' : metric.state === 'diagnostic' ? 'Diagnostic only' : 'Cannot determine'}</span></div>)}</div>
    <pre>{JSON.stringify(response, null, 2)}</pre>
  </details>
);
