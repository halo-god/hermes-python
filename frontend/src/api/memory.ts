import { http } from "@/api/client";

export interface Memory {
  notes: string | null;
  user_profile: string | null;
  soul: string | null;
}

export const memoryApi = {
  get: (): Promise<Memory> => http.get("/memory").then((r) => r.data),
  update: (payload: Partial<Memory>): Promise<Memory> =>
    http.put("/memory", payload).then((r) => r.data),
};
