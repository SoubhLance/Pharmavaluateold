export const evaluationData = {
  "provenance": "Generated from results/tables/FINAL_tests.csv, model comparison tables, configs/frozen.yaml, and report.md during the frontend build.",
  "finalTest": {
    "allTamperAuroc": {
      "value": 0.733928852080609,
      "ciLow": 0.72373734106884,
      "ciHigh": 0.7432603202299582
    },
    "tprAt5Fpr": {
      "value": 0.3527194399569198,
      "ciLow": null,
      "ciHigh": null
    },
    "falseCounterfeitOnGenuine": {
      "value": 0.0032310177705977385,
      "ciLow": 0,
      "ciHigh": 0.00819815316477468
    },
    "inconclusiveOrWorseOnGenuine": {
      "value": 0.5234248788368336,
      "ciLow": null,
      "ciHigh": null
    },
    "top1": {
      "value": 0.6849757673667205,
      "ciLow": null,
      "ciHigh": null
    },
    "top5": {
      "value": 0.8077544426494345,
      "ciLow": null,
      "ciHigh": null
    },
    "unknownRejection": {
      "value": 0.5,
      "ciLow": null,
      "ciHigh": null
    },
    "testCounts": {
      "genuine": 619,
      "syntheticTampers": 1857
    },
    "knownProducts": 480,
    "unknownTestCount": 126
  },
  "validationComparison": [
    {
      "name": "anomalydino_c8",
      "auroc": 0.7498955909551936,
      "tprAt5Fpr": 0.4189189189189189
    },
    {
      "name": "patchcore_wide_resnet50_2_r10",
      "auroc": 0.7001670544716903,
      "tprAt5Fpr": 0.3738738738738739
    },
    {
      "name": "efficientad_s",
      "auroc": 0.5452246246509657,
      "tprAt5Fpr": null
    }
  ],
  "calibrationRange": {
    "min": 35.752079010009766,
    "max": 51.50809860229492,
    "count": 260
  },
  "thresholds": {
    "tau": 0.8538066148757935,
    "alphaCounterfeit": 0.01,
    "alphaGenuine": 0.5
  }
} as const;
