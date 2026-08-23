export type ManualStatus = "processing" | "ready" | "error";

export interface Manual {
  id: string;
  title: string;
  filename: string;
  num_pages: number;
  num_chunks: number;
  chunk_chars: number;
  chunk_overlap_chars: number;
  embedding_model: string;
  status: ManualStatus;
  progress: number;
  error_message: string | null;
  experiment: boolean;
  created_at: string;
}

export interface RetrievedChunk {
  text: string;
  pages: string;
  distance: number;
}

export interface QueryResult {
  answer: string;
  cited_pages: number[];
  retrieved_pages: number[];
  chunks: RetrievedChunk[];
  latency_ms: number;
  usage: { input_tokens: number; output_tokens: number };
  cost_usd: number;
  not_found: boolean;
  provider: string;
  model: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  question?: string;
  result?: QueryResult;
  error?: string;
  pending?: boolean;
}

export interface EvalRunSummary {
  id: string;
  label: string | null;
  timestamp: string | null;
  config: Record<string, unknown> | null;
  aggregates: Record<string, number> | null;
}

export interface EvalQuestionRow {
  id: string;
  question: string;
  category: string;
  correct_answer: string;
  source_pages: number[];
  generated_answer: string;
  retrieval_hit: boolean;
  retrieved_pages: number[];
  correctness: number;
  correctness_reasoning: string;
  faithful: boolean;
  faithfulness_issues: string[];
  latency_ms: number;
  cost_usd: number;
}

export interface EvalRunDetail extends EvalRunSummary {
  questions: EvalQuestionRow[];
}
