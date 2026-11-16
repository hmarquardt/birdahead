export type Kind = "photo" | "audio";
export interface Bin {
  species_code: string;
  start: string;
  end: string;
  frequency: number | null;
  source_value?: number | null;
  sample_size: number | null;
  value_status?: string;
}
export interface OccurrenceProfile {
  metadata: {
    start_year: number;
    end_year: number;
    source_sha256: string;
    [key: string]: unknown;
  };
  rows: Bin[];
}
export interface Asset {
  id: string;
  kind: Kind;
  species_code: string;
  local_path: string;
  sha256: string;
  creator: string;
  source_url: string;
  license_url: string;
  attribution: string | null;
  vocalization: string | null;
  target_bbox_xyxy: number[] | null;
  license_code?: string | null;
  source?: string | null;
  sex?: string | null;
  age?: string | null;
  plumage?: string | null;
  derivative_of?: unknown;
  technical_metrics?: Record<string, unknown> | null;
  [key: string]: unknown;
}
export interface Species {
  ebird_species_code: string;
  common_name: string;
  scientific_name: string;
  pilot?: boolean;
  priority_rank?: number | null;
  confusion_pair?: Record<string, unknown> | null;
  selection_rationale?: string[];
  [key: string]: unknown;
}
export interface Release {
  schema: string;
  id: string;
  species: Species[];
  counties: Record<string, string>;
  profiles: Record<string, OccurrenceProfile>;
  assets: Asset[];
  compatibility_key?: string;
  coverage?: Record<string, Record<string, number | boolean>>;
  coverage_summary?: Record<string, unknown>;
  data_vintage?: Record<string, unknown>;
  confusion_pairs?: Array<{ left: string; right: string }>;
  limitations?: string[];
  universe?: Record<string, unknown>;
}
export interface Priority {
  species_code: string;
  current_reporting_frequency: number | null;
  future_14_28_day_max: number | null;
  approaching_window_rise: number | null;
  learning_priority: number | null;
  sample_size: number | null;
  bin_start: string | null;
  bin_end: string | null;
}
