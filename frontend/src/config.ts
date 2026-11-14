/**
 * API configuration for PharmaValuate frontend.
 *
 * In dev: Vite proxy forwards /health and /screen to http://127.0.0.1:8000
 * In prod: FastAPI serves the frontend build directly on the same origin.
 *
 * If targeting a custom backend host or port, define VITE_API_BASE_URL.
 */

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';

export const API_ENDPOINTS = {
  health: `${API_BASE_URL}/health`,
  screen: `${API_BASE_URL}/screen`,
} as const;

export const FROZEN_THRESHOLDS = {
  tau: 0.8538,
  alpha_cf: 0.01,
  alpha_gen: 0.50,
} as const;

export const DISCLAIMER_TEXT = 'Screening aid, verify manually';

