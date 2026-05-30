export type ChapterId = "1_droom" | "2_niche" | "3_waar" | "4_vergunningen" | "5_pakket";

export interface DreamProfile {
  sector?: string;
  sector_group?: string;
  nace_code?: string;
  scale?: string;
  seats_guess?: number | null;
  partners_guess?: number | null;
  budget_eur_guess?: number | null;
  vibe?: string;
  neighbourhood_anchor?: string;
  founder_quote?: string;
  confidence?: number;
}

export interface ChapterState {
  current_chapter: ChapterId;
  dream_profile: DreamProfile | null;
  niche_signals: Record<string, unknown> | null;
  candidate_locations: unknown[] | null;
  chosen_location: { address?: string; wijk_nl?: string; coordinates?: [number, number] } | null;
  permit_checklist: unknown[] | null;
  subsidies: unknown[] | null;
  legal_form: Record<string, unknown> | null;
  dream_narrative: string | null;
  tuesday_morning: string | null;
  package_url: string | null;
}

export interface AgentAction {
  type: string;
  dataset_id?: string;
  markers?: { coordinates: [number, number]; label?: string }[];
  field?: string;
  patch?: Record<string, unknown>;
  [k: string]: unknown;
}

export interface GeoFeature {
  type: "Feature";
  geometry: { type: string; coordinates: number[] | number[][] | number[][][] };
  properties: Record<string, unknown>;
}
export interface FeatureCollection {
  type: "FeatureCollection";
  features: GeoFeature[];
}

export interface TransientDataset {
  dataset_id: string;
  feature_count?: number;
  geojson?: FeatureCollection;
  ranked?: unknown[];
}

export interface AgentResponse {
  reply: string;
  actions: AgentAction[];
  datasets: Record<string, TransientDataset>;
  chapter_state: ChapterState;
  chapter_transitioned: boolean;
  reply_source?: string;
  debug_id?: string;
  session_id: string;
}
