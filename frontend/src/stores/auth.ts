import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { authApi, type LoginPayload } from "@/api/auth";
import { tokenStore } from "@/api/client";
import type { User } from "@/types";

export const useAuthStore = defineStore("auth", () => {
  const user = ref<User | null>(null);
  const ready = ref(false); // initial session check completed

  const isAuthenticated = computed(() => !!user.value);
  const isAdmin = computed(
    () => user.value?.role === "super_admin" || user.value?.role === "admin",
  );

  async function login(payload: LoginPayload) {
    const res = await authApi.login(payload);
    tokenStore.set(res.access_token, res.refresh_token);
    user.value = res.user;
    return res.user;
  }

  /** Restore session on app boot (page refresh). */
  async function bootstrap() {
    if (!tokenStore.access && !tokenStore.refresh) {
      ready.value = true;
      return;
    }
    try {
      user.value = await authApi.me();
    } catch {
      tokenStore.clear();
      user.value = null;
    } finally {
      ready.value = true;
    }
  }

  async function logout() {
    try {
      await authApi.logout(tokenStore.refresh);
    } catch {
      /* best-effort */
    }
    tokenStore.clear();
    user.value = null;
  }

  return { user, ready, isAuthenticated, isAdmin, login, bootstrap, logout };
});
