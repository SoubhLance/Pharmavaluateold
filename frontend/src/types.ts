/**
 * TypeScript types for PharmaValuate screening interface.
 * Pill stream only. Screening aid, verify manually.
 */

export interface QualityThresholds {
  blur_min?: number;
  glare_max?: number;
  lum_min?: number;
  lum_max?: number;
}

export interface QualityDetails {
  passed: boolean;
  blur?: number;
  glare?: number;
  mean_lum?: number;
  dark?: number;
  thresholds?: QualityThresholds;
}

export interface Top5Detail {
  product_id: string;
  similarity: number;
}

export type ScreeningLabel =
  | 'Likely Genuine'
  | 'Inconclusive'
  | 'Likely Counterfeit'
  | 'Retake Required'
  | 'Unknown Product';

export interface ScreenResponse {
  label: ScreeningLabel;
  p_value: number | null;
  anomaly_score: number | null;
  product_id: string | null;
  best_similarity: number | null;
  top5: string[] | null;
  top5_details: Top5Detail[] | null;
  quality: QualityDetails;
  disclaimer: string;
}

export interface HealthResponse {
  status: string;
  device: string;
  stream: string;
  gallery_products: number;
  disclaimer: string;
}

export interface ScreenHistoryItem {
  id: string;
  timestamp: Date;
  fileName: string;
  thumbnailUrl: string;
  result: ScreenResponse;
}

