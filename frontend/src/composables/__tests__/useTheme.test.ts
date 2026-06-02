import { describe, it, expect, vi } from "vitest";

// Mock matchMedia for jsdom
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })),
});

describe("useTheme composable", () => {
  it("exports useTheme function", async () => {
    const mod = await import("@/composables/useTheme");
    expect(typeof mod.useTheme).toBe("function");
  });

  it("returns theme, toggleTheme, setTheme", async () => {
    const { useTheme } = await import("@/composables/useTheme");
    const api = useTheme();
    expect(api.theme).toBeDefined();
    expect(typeof api.toggleTheme).toBe("function");
    expect(typeof api.setTheme).toBe("function");
    expect(["light", "dark"]).toContain(api.theme.value);
  });

  it("toggleTheme changes theme value", async () => {
    const { useTheme } = await import("@/composables/useTheme");
    const { theme, toggleTheme } = useTheme();
    const before = theme.value;
    toggleTheme();
    expect(theme.value).not.toBe(before);
  });

  it("setTheme explicitly sets theme", async () => {
    const { useTheme } = await import("@/composables/useTheme");
    const { theme, setTheme } = useTheme();
    setTheme("dark");
    expect(theme.value).toBe("dark");
    setTheme("light");
    expect(theme.value).toBe("light");
  });
});
