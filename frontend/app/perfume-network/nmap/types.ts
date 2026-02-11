export type NMapNode = {
  id: string;
  type: "perfume" | "accord";
  label: string;
  brand?: string;
  image?: string;
  primary_accord?: string;
  accords?: string[];
  seasons?: string[];
  occasions?: string[];
  genders?: string[];
  register_status?: string | null;
};

export type NMapEdge = {
  from: string;
  to: string;
  type: "HAS_ACCORD" | "SIMILAR_TO";
  weight: number;
};

export type NMapAnalysisSummary = {
  top_notes: string[];
  middle_notes: string[];
  base_notes: string[];
  mood_keywords: string[];
  representative_color?: string;
  analysis_text?: string;
};

export type NMapResponse = {
  nodes: NMapNode[];
  edges: NMapEdge[];
  summary: NMapAnalysisSummary;
  meta: Record<string, any>;
};

export type NetworkNode = NMapNode;
export type NetworkEdge = NMapEdge;

export type NetworkMeta = {
  perfume_count: number;
  accord_count: number;
  edge_count: number;
  accord_edges: number;
  similarity_edges: number;
  similarity_edges_high: number;
  min_similarity: number;
  top_accords: number;
  candidate_pairs: number;
  built_at: string;
  build_seconds: number;
  max_perfumes?: number | null;
};

export type NetworkPayload = {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  meta: NetworkMeta;
};

export type LabelsData = {
  perfume_names: Record<string, string>;
  brands: Record<string, string>;
  accords: Record<string, string>;
  seasons: Record<string, string>;
  occasions: Record<string, string>;
  genders: Record<string, string>;
};

export type FilterOptions = {
  accords: string[];
  brands: string[];
  seasons: string[];
  occasions: string[];
  genders: string[];
};
