export type DocType = 'speech' | 'statement' | 'minutes' | 'testimony';

export interface Source {
  chunk_id: string;
  doc_id: string;
  text: string;
  score: number;
  rerank_score: number;
  doc_type: DocType;
  speaker: string | null;
  date: string;
  title: string;
  url: string;
}

export interface QueryResponse {
  answer: string;
  sources: Source[];
  tool_calls_made: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  timestamp: Date;
}
