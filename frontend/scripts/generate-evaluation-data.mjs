import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const projectRoot = path.resolve(frontendRoot, '..');

function parseCsv(text) {
  const [headerLine, ...lines] = text.trim().split(/\r?\n/);
  const splitLine = (line) => {
    const cells = [];
    let cell = '';
    let quoted = false;
    for (let i = 0; i < line.length; i += 1) {
      const char = line[i];
      if (char === '"' && line[i + 1] === '"' && quoted) { cell += '"'; i += 1; }
      else if (char === '"') quoted = !quoted;
      else if (char === ',' && !quoted) { cells.push(cell); cell = ''; }
      else cell += char;
    }
    cells.push(cell);
    return cells;
  };
  const headers = splitLine(headerLine);
  return lines.map((line) => Object.fromEntries(splitLine(line).map((value, i) => [headers[i], value])));
}

const [finalTests, patchcore, anomalydino, efficientad, frozen, report] = await Promise.all([
  readFile(path.join(projectRoot, 'results/tables/FINAL_tests.csv'), 'utf8'),
  readFile(path.join(projectRoot, 'results/tables/grid_patchcore_pill.csv'), 'utf8'),
  readFile(path.join(projectRoot, 'results/tables/grid_anomalydino_pill.csv'), 'utf8'),
  readFile(path.join(projectRoot, 'results/tables/effad_S_pill_s0.csv'), 'utf8'),
  readFile(path.join(projectRoot, 'configs/frozen.yaml'), 'utf8'),
  readFile(path.join(projectRoot, 'report.md'), 'utf8'),
]);

const finalRows = parseCsv(finalTests);
const finalMetric = (includes) => {
  const row = finalRows.find((candidate) => includes.every((word) => candidate.metric.toLowerCase().includes(word)));
  return row ? { value: Number(row.value), ciLow: row.ci_lo ? Number(row.ci_lo) : null, ciHigh: row.ci_hi ? Number(row.ci_hi) : null } : null;
};
const comparison = (csv, name) => {
  const rows = parseCsv(csv);
  const row = rows.find((candidate) => candidate.name === name);
  return row ? { name, auroc: Number(row.val_auroc), tprAt5Fpr: Number(row.tpr_at_5fpr) } : null;
};

const scoreList = frozen.split(/cal_scores:\s*\r?\n/)[1]?.split(/\r?\n\s{2}[a-zA-Z_]+:/, 1)[0];
if (!scoreList) throw new Error('Could not read calibration scores from configs/frozen.yaml');
const calibrationScores = [...scoreList.matchAll(/-\s+([-+\d.eE]+)/g)].map((match) => Number(match[1]));
const testCounts = report.match(/([\d,]+) genuine \+ ([\d,]+) synthetic tampers/);
const products = report.match(/\((\d+) products\)/);
const unknownCounts = report.match(/Unknown-Product Rejection Rate[^\n]*\((\d+)\s*\/\s*(\d+)\)/);
const yamlNumber = (key) => {
  const match = frozen.match(new RegExp(`^\\s+${key}:\\s*([-+\\d.eE]+)`, 'm'));
  return match ? Number(match[1]) : null;
};

const payload = {
  provenance: 'Generated from results/tables/FINAL_tests.csv, model comparison tables, configs/frozen.yaml, and report.md during the frontend build.',
  finalTest: {
    allTamperAuroc: finalMetric(['auroc all tampers']),
    tprAt5Fpr: finalMetric(['tpr@5%fpr']),
    falseCounterfeitOnGenuine: finalMetric(['false likely-counterfeit rate']),
    inconclusiveOrWorseOnGenuine: finalMetric(['inconclusive-or-worse rate on genuine']),
    top1: finalMetric(['identification top-1']),
    top5: finalMetric(['identification top-5']),
    unknownRejection: finalMetric(['unknown-product rejection rate']),
    testCounts: testCounts ? { genuine: Number(testCounts[1].replaceAll(',', '')), syntheticTampers: Number(testCounts[2].replaceAll(',', '')) } : null,
    knownProducts: products ? Number(products[1]) : null,
    unknownTestCount: unknownCounts ? Number(unknownCounts[2]) : null,
  },
  validationComparison: [
    comparison(anomalydino, 'anomalydino_c8'),
    comparison(patchcore, 'patchcore_wide_resnet50_2_r10'),
    (() => { const row = parseCsv(efficientad).find((candidate) => candidate.model === 'efficientad_s'); return row ? { name: 'efficientad_s', auroc: Number(row.val_auroc), tprAt5Fpr: null } : null; })(),
  ].filter(Boolean),
  calibrationRange: { min: Math.min(...calibrationScores), max: Math.max(...calibrationScores), count: calibrationScores.length },
  thresholds: { tau: yamlNumber('tau'), alphaCounterfeit: yamlNumber('alpha_cf'), alphaGenuine: yamlNumber('alpha_gen') },
};

const outputDir = path.join(frontendRoot, 'src/generated');
await mkdir(outputDir, { recursive: true });
await writeFile(path.join(outputDir, 'evaluationData.ts'), `export const evaluationData = ${JSON.stringify(payload, null, 2)} as const;\n`, 'utf8');
