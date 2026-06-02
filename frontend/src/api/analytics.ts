import { http } from "./client";

export interface DayCount {
  date: string;
  count: number;
}

export interface AgentCount {
  agent_id: string;
  count: number;
}

export interface UsageStats {
  total_messages: number;
  total_conversations: number;
  tokens_total: number;
  messages_by_day: DayCount[];
  messages_by_role: Record<string, number>;
  top_agents: AgentCount[];
}

export const analyticsApi = {
  async usage(): Promise<UsageStats> {
    return (await http.get<UsageStats>("/analytics/usage")).data;
  },
};
