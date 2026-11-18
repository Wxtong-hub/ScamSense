export type RoleId = "lin" | "chen" | "wang";
export interface Role {
  id: RoleId;
  name: string;
  title: string;
}
export interface Training {
  session_id: string;
  phase: string;
  status: "active" | "completed" | "ended_early";
  version: number;
  roles: Role[];
  report_ready: boolean;
  expires_at: string;
}
export interface Message {
  id: string;
  role_id: RoleId;
  sender: "user" | "role";
  content: string;
  created_at: string;
  status: string;
}
export type Choice = "continue" | "decline" | "defer" | "verify_more";
export const choices: Record<Choice, string> = {
  continue: "继续了解",
  decline: "拒绝这次机会",
  defer: "暂缓决定",
  verify_more: "先进一步核实",
};
export interface Evidence {
  message_id: string | null;
  role_id: RoleId | null;
  excerpt: string;
}
export interface Dimension {
  key: string;
  label: string;
  weight: number;
  score: number | null;
  explanation: string;
  evidence: Evidence[];
}
export interface Report {
  total: number | null;
  decision: { choice: Choice; reason: string } | null;
  dimensions: Dimension[];
  strengths: string[];
  suggestions: string[];
  rubric_version: string;
}
export const people: Role[] = [
  { id: "lin", name: "林悦", title: "企业人事专员" },
  { id: "chen", name: "陈浩", title: "项目招聘顾问" },
  { id: "wang", name: "王宇", title: "校园朋友" },
];
export const questions: Record<RoleId, string[]> = {
  lin: [
    "这个岗位的日常工作和招聘流程是什么？",
    "签约单位和招聘主体是一家吗？",
    "这个阶段需要哪些资料？",
  ],
  chen: [
    "这次招聘由哪家单位负责，能说明授权关系吗？",
    "预登记需要哪些资料，保存多久？",
    "这个岗位的工作内容是什么？",
  ],
  wang: [
    "你是亲自核实过，还是只在群里看到的？",
    "你了解这个岗位的面试流程吗？",
    "这份消息有原始出处吗？",
  ],
};
export const phases: Record<string, string> = {
  S0: "初始接触",
  S1: "了解机会",
  S2: "候选人预登记",
  S3: "出现风险线索",
  S4: "主动核实",
  S5: "最终决策",
  S6: "训练复盘",
};
