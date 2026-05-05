/** Chat types mirroring `silvercurrent.schemas.chat`. */

export type ChatRole = "user" | "assistant";

export type RoutedAgent = "operator" | "analyst" | "clarify" | "out_of_scope";

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

export type RoutingInfo = {
  agent: RoutedAgent;
  rationale: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
};

export type ChatResponse = {
  user_turn: ChatTurn;
  assistant_turn: ChatTurn;
  agent_used: RoutedAgent;
  usage: ChatUsage;
  routing: RoutingInfo;
};

export type ChatRequest = {
  scope: string;
  message: string;
};
