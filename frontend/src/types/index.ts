// Step status state machine
export type StepStatus =
  | 'locked'
  | 'active'
  | 'ai_thinking'
  | 'ai_suggested'
  | 'user_confirmed'
  | 'completed';

export interface StepState {
  step_number: number;
  status: StepStatus;
  ai_suggestion: Record<string, unknown> | null;
  user_input: Record<string, unknown> | null;
  confidence: number | null;
  error: string | null;
  updated_at: string;
}

export interface SessionState {
  session_id: string;
  version: number;
  source_db_url: string;
  source_db_type: string;
  metadata_snapshot: Record<string, unknown> | null;
  business_process: string;
  grain_description: string;
  selected_dimensions: string[];
  selected_measures: Record<string, unknown>[];
  dimensional_model: Record<string, unknown> | null;
  generated_ddl: string;
  generated_etl: string;
  generated_dbt: Record<string, string>;
  steps: StepState[];
  step_decisions: Record<string, unknown>[];
  created_at: string;
  updated_at: string;
}

// Metadata types
export interface ColumnInfo {
  name: string;
  data_type: string;
  nullable: boolean;
  is_primary_key: boolean;
  default: string | null;
  comment: string | null;
  distinct_count: number | null;
  null_count: number | null;
  sample_values: string[];
}

export interface RelationshipInfo {
  source_table: string;
  source_column: string;
  target_table: string;
  target_column: string;
  is_inferred: boolean;
  confidence: number;
}

export interface TableInfo {
  name: string;
  schema_name: string;
  columns: ColumnInfo[];
  row_count: number | null;
  comment: string | null;
  primary_key: string[];
}

export interface MetadataSnapshot {
  tables: TableInfo[];
  relationships: RelationshipInfo[];
  database_name: string;
  database_type: string;
  discovered_at: string;
}

// Step definitions
export const STEPS = [
  { number: 1, name: '连接数据源', nameEn: 'Connect' },
  { number: 2, name: '元数据发现', nameEn: 'Discover' },
  { number: 3, name: '选择业务过程', nameEn: 'Business Process' },
  { number: 4, name: '定义粒度', nameEn: 'Grain' },
  { number: 5, name: '选择维度', nameEn: 'Dimensions' },
  { number: 6, name: '定义度量', nameEn: 'Measures' },
  { number: 7, name: '生成模型', nameEn: 'Model' },
  { number: 8, name: '生成代码', nameEn: 'Code' },
] as const;
