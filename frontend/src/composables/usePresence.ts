/**
 * Presence composable: heartbeat + batch query.
 *
 * Usage:
 *   const { startHeartbeat, stopHeartbeat, queryPresence, statuses } = usePresence();
 *   startHeartbeat();  // call on login
 *   stopHeartbeat();   // call on logout
 *   await queryPresence(['user-id-1', 'user-id-2']);
 */
import { ref } from "vue";
import { http } from "@/api/client";

const statuses = ref<Record<string, string>>({});
let heartbeatTimer: ReturnType<typeof setInterval> | null = null;

export function usePresence() {
  async function sendHeartbeat() {
    try {
      await http.post("/presence/heartbeat");
    } catch {
      // non-fatal
    }
  }

  function startHeartbeat() {
    if (heartbeatTimer) return;
    sendHeartbeat();
    heartbeatTimer = setInterval(sendHeartbeat, 30_000);
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
  }

  async function queryPresence(userIds: string[]): Promise<Record<string, string>> {
    if (!userIds.length) return {};
    try {
      const res = await http.post<{ statuses: Record<string, string> }>("/presence/query", { user_ids: userIds });
      statuses.value = { ...statuses.value, ...res.data.statuses };
      return res.data.statuses;
    } catch {
      return {};
    }
  }

  function getStatus(userId: string): "online" | "offline" {
    return (statuses.value[userId] as "online" | "offline") || "offline";
  }

  return { statuses, startHeartbeat, stopHeartbeat, queryPresence, getStatus };
}
