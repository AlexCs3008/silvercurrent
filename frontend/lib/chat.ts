/** Chat types mirroring `silvercurrent.schemas.chat`. */

export type ChatRole = "user" | "assistant";

export type ChatTurn = {
  id: string;
  scope: string;
  role: ChatRole;
  content: string;
  created_at: string;
};

export type ChatUsage = {
  input_tokens: number;
  output_tokens: number;
  model: string;
  iterations: number;
};

export type ChatResponse = {
  user_turn: ChatTurn;
  assistant_turn: ChatTurn;
  usage: ChatUsage;
};

export type ChatRequest = {
  scope: string;
  message: string;
};
