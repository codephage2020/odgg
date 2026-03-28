// Types for the Modeling Brief Editor

export type BriefStatus = 'draft' | 'review' | 'approved' | 'exported';

export type SectionType =
  | 'business_process'
  | 'grain'
  | 'dimension'
  | 'measure'
  | 'relationship'
  | 'notes';

export type DimensionType = 'regular' | 'degenerate' | 'junk' | 'role_playing';

export type AggregationType =
  | 'sum'
  | 'count'
  | 'avg'
  | 'min'
  | 'max'
  | 'count_distinct';

export interface BriefSection {
  id: string;
  brief_id: string;
  section_type: SectionType;
  position: number;
  content: string;
  ai_drafts: string[];
  user_edited: boolean;
  name?: string | null;
  source_table?: string | null;
  source_columns?: string[] | null;
  source_column?: string | null;
  data_type?: string | null;
  dimension_type?: DimensionType | null;
  scd_type?: number | null;
  aggregation_type?: AggregationType | null;
  from_dimension?: string | null;
  to_fact?: string | null;
  join_column?: string | null;
  cardinality?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Brief {
  id: string;
  title: string;
  status: BriefStatus;
  source_db_type: string;
  database_name: string;
  metadata_snapshot?: Record<string, unknown> | null;
  selected_tables?: string[] | null;
  sections: BriefSection[];
  created_at: string;
  updated_at: string;
}

export interface BriefListItem {
  id: string;
  title: string;
  status: BriefStatus;
  database_name: string;
  section_count: number;
  created_at: string;
  updated_at: string;
}

// SSE event types for cascade drafting
export interface DraftingEvent {
  section: string;
}

export interface SectionReadyEvent {
  section: string;
  data: BriefSection;
}

export interface DraftDoneEvent {
  sections_created: number;
}

export interface DraftErrorEvent {
  error: string;
}

// Section display configuration
export const SECTION_LABELS: Record<SectionType, string> = {
  business_process: '业务过程',
  grain: '粒度',
  dimension: '维度',
  measure: '度量',
  relationship: '关系',
  notes: '备注',
};

export const SECTION_ICONS: Record<SectionType, string> = {
  business_process: '🏢',
  grain: '🔍',
  dimension: '📐',
  measure: '📊',
  relationship: '🔗',
  notes: '📝',
};
