import { defineStore } from "pinia";
import { ref } from "vue";

export interface Toast {
  id: number;
  message: string;
  kind: "ok" | "error" | "info" | "warn";
}

export interface Notification {
  id: number;
  title: string;
  body: string;
  kind: "info" | "success" | "warn" | "error";
  read: boolean;
  ts: string;
  link?: string;
}

let _tid = 0;
let _nid = 0;

export const useNotificationStore = defineStore("notifications", () => {
  const toasts = ref<Toast[]>([]);
  const inbox = ref<Notification[]>([]);

  function toast(message: string, kind: Toast["kind"] = "ok") {
    const id = ++_tid;
    toasts.value.push({ id, message, kind });
    setTimeout(() => dismiss(id), 2800);
  }
  function dismiss(id: number) {
    toasts.value = toasts.value.filter((t) => t.id !== id);
  }

  function push(n: Omit<Notification, "id" | "read" | "ts">) {
    inbox.value.unshift({ ...n, id: ++_nid, read: false, ts: new Date().toISOString() });
    toast(n.title, n.kind === "error" ? "error" : n.kind === "warn" ? "warn" : "info");
  }
  function markRead(id: number) {
    const n = inbox.value.find((x) => x.id === id);
    if (n) n.read = true;
  }
  function markAllRead() {
    inbox.value.forEach((n) => (n.read = true));
  }
  function remove(id: number) {
    inbox.value = inbox.value.filter((n) => n.id !== id);
  }

  const unreadCount = () => inbox.value.filter((n) => !n.read).length;

  return { toasts, inbox, toast, dismiss, push, markRead, markAllRead, remove, unreadCount };
});
