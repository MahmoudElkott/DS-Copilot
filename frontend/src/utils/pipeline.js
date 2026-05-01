export const VALID_STEP_KEYS = [
  'data_prep',
  'eda',
  'features',
  'training',
  'evaluation',
  'reporting',
  'deployment',
];

export const STAGE_TO_STEP = {
  data_preparation: 'data_prep',
  ingestion: 'data_prep',
  profiling: 'data_prep',
  cleaning: 'data_prep',
  eda: 'eda',
  feature_engineering: 'features',
  model_training: 'training',
  model_evaluation: 'evaluation',
  reporting: 'reporting',
  deployment: 'deployment',
};

const LEGACY_STEP_KEYS = {
  data_ingest: 'data_prep',
  data_ingestion: 'data_prep',
  data_cleaning: 'data_prep',
  model_selection: 'features',
  code_writing: 'training',
  execute_code: 'training',
  testing: 'evaluation',
  optimization: 'evaluation',
  documentation: 'reporting',
  code_writer: 'training',
};

export function normalizeStepKey(raw) {
  if (!raw) return null;
  const lower = String(raw).trim().toLowerCase();

  if (VALID_STEP_KEYS.includes(lower)) return lower;
  if (STAGE_TO_STEP[lower]) return STAGE_TO_STEP[lower];
  if (LEGACY_STEP_KEYS[lower]) return LEGACY_STEP_KEYS[lower];

  const normalized = lower.replace(/[\s-]+/g, '_');
  if (VALID_STEP_KEYS.includes(normalized)) return normalized;
  if (STAGE_TO_STEP[normalized]) return STAGE_TO_STEP[normalized];
  if (LEGACY_STEP_KEYS[normalized]) return LEGACY_STEP_KEYS[normalized];

  return null;
}

export function stageToRunningStep(stage) {
  return STAGE_TO_STEP[stage] || normalizeStepKey(stage);
}

export function inferStepKeyFromAgent(agent) {
  if (!agent) return null;
  const value = String(agent).toLowerCase();

  if (value.includes('deployment') || value.includes('deploy')) return 'deployment';
  if (value.includes('report') || value.includes('documentation')) return 'reporting';
  if (value.includes('evaluation') || value.includes('testing') || value.includes('optimization')) return 'evaluation';
  if (value.includes('training') || value.includes('code_writing') || value.includes('execute_code') || value.includes('code_writer')) return 'training';
  if (value.includes('feature') || value.includes('model_selection')) return 'features';
  if (value.includes('eda')) return 'eda';
  if (value.includes('data') || value.includes('ingest') || value.includes('clean') || value.includes('profiling')) return 'data_prep';

  return normalizeStepKey(value);
}
