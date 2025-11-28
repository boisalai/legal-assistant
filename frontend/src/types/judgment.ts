export interface Judgment {
  id: string;
  title: string;
  citation?: string;
  tribunal?: string;
  date?: string;
  plaintiff?: string;
  defendant?: string;
  domain?: string;
  original_text: string;
  created_at: string;
  updated_at: string;
}

export interface CaseBrief {
  id: string;
  judgment_id: string;
  facts: string;
  issues: string[];
  rules: string[];
  ratio_decidendi: string;
  obiter_dicta?: string;
  conclusion: string;
  created_at: string;
}

export interface SummarizeResponse {
  judgment: Judgment;
  case_brief: CaseBrief;
}
