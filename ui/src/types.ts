// Shapes mirror the backend (metrics.json + run artifacts) so swapping the mock
// fixture for the live API is a drop-in change.

export interface Metrics {
  n_items: number;
  n_records: number;
  n_errors: number;
  agreement: number;
  score_spread: number;
  position_consistency: number | null;
  position_consistent_agreement: number | null;
}

export interface Edit {
  iter: number;
  n_errors: number;
  failure_modes: string[];
  strategies: string[];
  procedure_edits: string[];
}

export type Mode = "anchored" | "unanchored";

export interface ModeResult {
  mode: Mode;
  history: Metrics[]; // index 0 = baseline
  edits: Edit[];
  skills: string[]; // skills[t] = full SKILL.md text at iteration t
}

export interface ItemRecord {
  item_id: string;
  task_type: string;
  system_prompt: string;
  question: string;
  answer_a: string;
  answer_b: string;
  pairing: string; // e.g. "A-vs-C"
  verdict: "A" | "B";
  correct: boolean;
  margin: number;
  rationale: string;
  fooled_by?: "fluency" | "format" | "length";
}

export interface RunBundle {
  run_id: string;
  n_dev: number;
  n_heldout: number;
  unseen_heldout_types: string[];
  results: Record<Mode, ModeResult>;
  items: ItemRecord[];
}

export interface ExperimentVariant {
  id: string;
  label: string;
  learns: boolean;
  teacher_model: string | null;
  method: string;
  trains_on: string;
  agreement: number;
  pos_consistency: number;
  cost_usd: number | null;
  verdict: string;
  note: string;
  peak?: number;
  curve_run?: string | null;
}

export interface ExperimentFindings {
  promising: string[];
  limited: string[];
}

export interface ExperimentData {
  benchmark: string;
  test_set: string;
  train_set: string;
  judge_model: string;
  training_means: string;
  variants: ExperimentVariant[];
  findings: ExperimentFindings;
}

export interface SftEvalSubsetMetrics {
  n_items: number;
  n_records: number;
  n_errors: number;
  agreement: number;
  score_spread: number;
  position_consistency: number;
  position_consistent_agreement: number;
}

export interface SftEvalVariant {
  label: string;
  model: string;
  dataset: string;
  n_items: number;
  overall: SftEvalSubsetMetrics;
  per_subset: Record<string, SftEvalSubsetMetrics>;
  usage: {
    calls: number;
    input_tokens: number;
    output_tokens: number;
    cost_usd: number;
  };
}

export interface SftEvalData {
  dataset: string;
  policy: string;
  variants: SftEvalVariant[];
  delta: {
    agreement_pp: number;
    position_consistency_pp: number;
    position_consistent_agreement_pp: number;
  };
}
