import React from 'react';
import { evaluationData as data } from '../generated/evaluationData';

const percent = (value: number | null | undefined, digits = 1) => value === null || value === undefined ? '—' : `${(value * 100).toFixed(digits)}%`;
const decimal = (value: number | null | undefined, digits = 3) => value === null || value === undefined ? '—' : value.toFixed(digits);

const pipeline = [
  { no: '01', label: 'Capture quality', model: 'OpenCV measurements', detail: 'Checks sharpness, glare and luminance before inference.' },
  { no: '02', label: 'Product retrieval', model: 'DINOv2 · ViT-S/14', detail: `Matches four image rotations against ${data.finalTest.knownProducts ?? 'the'} frozen product references.` },
  { no: '03', label: 'Patch comparison', model: 'AnomalyDINO · c8', detail: 'Compares local patch tokens with the selected product’s genuine memory.' },
  { no: '04', label: 'Conformal decision', model: 'Genuine calibration set', detail: 'Maps the anomaly score to a finite-sample conformal p-value and screening label.' },
];

export const AboutMethod: React.FC = () => (
  <div className="method-page">
    <section className="method-hero">
      <div><span className="eyebrow">METHOD NOTE · PILL STREAM</span><h1>How the screening instrument works</h1><p>A genuine-only visual anomaly pipeline for medicine photographs. Each stage answers a different question, from image usability to visual consistency with frozen references.</p></div>
      <div className="method-hero-mark" aria-hidden="true"><div className="method-orbit"/><div className="method-cross">+</div><span>PV<br/>01</span></div>
    </section>

    <section className="pipeline-section" aria-labelledby="pipeline-title">
      <div className="method-section-heading"><div><span className="eyebrow">INFERENCE SEQUENCE</span><h2 id="pipeline-title">Four stages. Four distinct signals.</h2></div><span className="method-section-code">LOCAL · FROZEN PIPELINE</span></div>
      <div className="pipeline-architecture">{pipeline.map((step, index) => <React.Fragment key={step.no}><article className="pipeline-node"><span className="pipeline-node-no">{step.no}</span><span className="pipeline-node-art" aria-hidden="true">{index === 0 ? '◉' : index === 1 ? '⌕' : index === 2 ? '▦' : '∿'}</span><span className="eyebrow">{step.model}</span><h3>{step.label}</h3><p>{step.detail}</p></article>{index < pipeline.length - 1 && <span className="pipeline-connector" aria-hidden="true">→</span>}</React.Fragment>)}</div>
    </section>

    <section className="method-explainer-grid">
      <article className="method-explainer-card"><span className="explainer-number">A</span><div><span className="eyebrow">IMAGE REPRESENTATION</span><h3>DINOv2 retrieval</h3><p>A frozen DINOv2 ViT-S/14 encoder represents the uploaded image at four rotations. Cosine similarity ranks the reference products; a best match below the configured τ is reported as <strong>Unknown Product</strong>.</p><div className="tau-callout"><span>IDENTIFICATION THRESHOLD τ</span><strong>{data.thresholds.tau.toFixed(4)}</strong><small>Similarity threshold · not a counterfeit threshold</small></div></div></article>
      <article className="method-explainer-card"><span className="explainer-number">B</span><div><span className="eyebrow">LOCAL VISUAL DEVIATION</span><h3>AnomalyDINO patch memory</h3><p>Patch tokens from the selected product image are compared with its genuine reference memory. The resulting distance is an anomaly score; it is not converted to a counterfeit probability.</p><div className="patch-visual" aria-label="Illustration of image patches compared to a reference memory"><span/><span/><span/><span/><i>↔</i><b/><b/><b/><b/></div></div></article>
      <article className="method-explainer-card conformal-explainer"><span className="explainer-number">C</span><div><span className="eyebrow">CALIBRATED SCREENING</span><h3>Conformal prediction</h3><p>The anomaly score is ranked against genuine calibration scores. The conformal p-value selects a screening band; it does not describe the probability that a pill is genuine.</p><div className="decision-ranges"><span className="range-counterfeit">p ≤ {data.thresholds.alphaCounterfeit.toFixed(2)}<small>Likely Counterfeit</small></span><span className="range-inconclusive">{data.thresholds.alphaCounterfeit.toFixed(2)} &lt; p ≤ {data.thresholds.alphaGenuine.toFixed(2)}<small>Inconclusive</small></span><span className="range-genuine">p &gt; {data.thresholds.alphaGenuine.toFixed(2)}<small>Likely Genuine</small></span></div></div></article>
    </section>

    <section className="benchmark-section" aria-labelledby="benchmark-title">
      <div className="method-section-heading"><div><span className="eyebrow">FROZEN TEST EVALUATION</span><h2 id="benchmark-title">Measured performance</h2></div><span className="synthetic-tag"><i/> SYNTHETIC STRESS TEST</span></div>
      <p className="benchmark-context">Final frozen benchmark values generated from the project’s test results. These figures describe a synthetic stress test and do not establish real-counterfeit accuracy.</p>
      <div className="benchmark-feature-grid">
        <article className="benchmark-feature benchmark-auroc"><span>ALL-TAMPER AUROC</span><strong>{decimal(data.finalTest.allTamperAuroc?.value)}</strong><div className="confidence-rail"><i style={{ left: `${(data.finalTest.allTamperAuroc?.ciLow ?? 0) * 100}%`, width: `${((data.finalTest.allTamperAuroc?.ciHigh ?? 0) - (data.finalTest.allTamperAuroc?.ciLow ?? 0)) * 100}%` }}/></div><small>95% CI {decimal(data.finalTest.allTamperAuroc?.ciLow)} – {decimal(data.finalTest.allTamperAuroc?.ciHigh)}</small></article>
        <article className="benchmark-feature"><span>TPR AT 5% FPR</span><strong>{percent(data.finalTest.tprAt5Fpr?.value)}</strong><small>True positive rate at the selected false-positive operating point</small></article>
        <article className="benchmark-feature"><span>FALSE COUNTERFEIT · GENUINE</span><strong>{percent(data.finalTest.falseCounterfeitOnGenuine?.value, 2)}</strong><small>Genuine test images flagged Likely Counterfeit</small></article>
        <article className="benchmark-feature"><span>GENUINE · INCONCLUSIVE OR WORSE</span><strong>{percent(data.finalTest.inconclusiveOrWorseOnGenuine?.value)}</strong><small>Conservative screening outcome rate on genuine images</small></article>
      </div>
      <div className="benchmark-secondary-grid"><BenchmarkStat label="Product retrieval · Top-1" value={percent(data.finalTest.top1?.value)} note="correct first match"/><BenchmarkStat label="Product retrieval · Top-5" value={percent(data.finalTest.top5?.value)} note="correct product in candidate set"/><BenchmarkStat label="Unknown-product rejection" value={percent(data.finalTest.unknownRejection?.value)} note={data.finalTest.unknownTestCount ? `${data.finalTest.unknownTestCount} unknown test products` : 'test evaluation'}/></div>
    </section>

    <section className="comparison-section" aria-labelledby="comparison-title">
      <div className="method-section-heading"><div><span className="eyebrow">MODEL SELECTION CONTEXT</span><h2 id="comparison-title">Validation AUROC comparison</h2></div><span className="method-section-code">VALIDATION · NOT FINAL TEST</span></div>
      <p className="benchmark-context">Candidate validation results from the evaluated PatchCore, AnomalyDINO and EfficientAD configurations. The displayed bars use AUROC on a 0–1 scale.</p>
      <div className="comparison-chart">{data.validationComparison.map((model) => <div className={`comparison-row ${model.name === 'anomalydino_c8' ? 'selected' : ''}`} key={model.name}><div className="comparison-label"><strong>{model.name === 'anomalydino_c8' ? 'AnomalyDINO c8' : model.name.startsWith('patchcore') ? 'PatchCore · Wide ResNet50-2' : 'EfficientAD-S'}</strong><span>{model.name === 'anomalydino_c8' ? 'Frozen method' : 'Evaluated candidate'}</span></div><div className="comparison-track"><i style={{ width: `${model.auroc * 100}%` }}/></div><strong className="comparison-value">{model.auroc.toFixed(3)}</strong><span className="comparison-tpr">TPR @ 5% FPR {model.tprAt5Fpr === null ? '—' : percent(model.tprAt5Fpr)}</span></div>)}</div>
    </section>

    <section className="dataset-section" aria-labelledby="dataset-title"><div className="method-section-heading"><div><span className="eyebrow">EVALUATION SCOPE</span><h2 id="dataset-title">What the numbers cover</h2></div></div><div className="dataset-stat-grid"><DatasetStat label="Catalog products" value={data.finalTest.knownProducts}/><DatasetStat label="Genuine test images" value={data.finalTest.testCounts?.genuine}/><DatasetStat label="Synthetic tamper images" value={data.finalTest.testCounts?.syntheticTampers}/><DatasetStat label="Genuine calibration images" value={data.calibrationRange.count}/><DatasetStat label="Unknown test products" value={data.finalTest.unknownTestCount}/></div><p className="dataset-footnote">Calibration score span: {data.calibrationRange.min.toFixed(2)}–{data.calibrationRange.max.toFixed(2)}. Counts and metrics are generated from the frozen configuration and project evaluation files.</p></section>

    <section className="limitations-section"><div className="limitations-symbol" aria-hidden="true">!</div><div><span className="eyebrow">SAFETY & LIMITATIONS</span><h2>Screening aid, verify manually.</h2><p>The benchmark uses synthetic image alterations. It has not been validated against real-world counterfeit medicines and cannot establish authenticity, safety or regulatory compliance.</p><ul><li>Image quality failure means the photo needs to be retaken; it does not mean the medicine is suspicious.</li><li>Unknown Product means the reference catalog could not identify the image confidently.</li><li>Likely Counterfeit is a thresholded anomaly screening alert, not a confirmed counterfeit finding.</li><li>Always use qualified professionals and regulatory or laboratory channels for verification.</li></ul></div></section>
    <div className="evaluation-source-note">Evaluation source: results/tables/FINAL_tests.csv · candidate comparison: results/tables/* · calibration reference: configs/frozen.yaml</div>
  </div>
);

const BenchmarkStat: React.FC<{ label: string; value: string; note: string }> = ({ label, value, note }) => <article className="benchmark-secondary-stat"><span>{label}</span><strong>{value}</strong><small>{note}</small></article>;
const DatasetStat: React.FC<{ label: string; value: number | null | undefined }> = ({ label, value }) => <article><strong>{value?.toLocaleString() ?? '—'}</strong><span>{label}</span></article>;
