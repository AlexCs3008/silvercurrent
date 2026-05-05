/** Analyze types mirroring `silvercurrent.schemas.analyze`. */

export type DealSheet = {
  id: string;
  listing_id: string;
  created_at: string;
  markdown: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  iterations: number;
};

export type AnalyzeUsage = {
  input_tokens: number;
  output_tokens: number;
  model: string;
  iterations: number;
};

export type AnalyzeResponse = {
  deal_sheet: DealSheet;
  usage: AnalyzeUsage;
};
