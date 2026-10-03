export type ChartSpec = {
  type: "bar" | "line" | "number" | "table";
  x: string | null;
  y: string[];
  title: string;
};

export type Answer = {
  summary: string;
  key_numbers: string[];
  chart: ChartSpec;
  caveats: string[];
  followups: string[];
};

export type Step = { node: string; ms: number | null; error: string | null };

export type Cell = string | number | boolean | null;

export type ResultTable = { columns: string[]; rows: Cell[][]; row_count: number };

export type UsageCall = {
  call: string;
  role: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cached?: boolean;
};

export type Usage = {
  calls: UsageCall[];
  input_tokens: number;
  output_tokens: number;
  steps: { node: string; ms: number }[];
};

export type Turn = {
  id: string;
  question: string;
  status: "running" | "done" | "error";
  steps: Step[];
  sql?: string;
  table?: ResultTable;
  answer?: Answer;
  understoodAs?: string | null;
  intent?: string;
  usage?: Usage;
  error?: string;
};