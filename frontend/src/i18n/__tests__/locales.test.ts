import { describe, it, expect, beforeEach } from "vitest";

describe("i18n locale files", () => {
  let zhCN: Record<string, any>;
  let en: Record<string, any>;

  beforeEach(async () => {
    zhCN = (await import("@/i18n/locales/zh-CN")).default;
    en = (await import("@/i18n/locales/en")).default;
  });

  it("zh-CN and en have the same top-level keys", () => {
    expect(Object.keys(zhCN).sort()).toEqual(Object.keys(en).sort());
  });

  it("nav section has matching keys", () => {
    expect(Object.keys(zhCN.nav).sort()).toEqual(Object.keys(en.nav).sort());
  });

  it("chat section has matching keys", () => {
    expect(Object.keys(zhCN.chat).sort()).toEqual(Object.keys(en.chat).sort());
  });

  it("common section has matching keys", () => {
    expect(Object.keys(zhCN.common).sort()).toEqual(Object.keys(en.common).sort());
  });

  it("all zh-CN values are non-empty strings", () => {
    function checkValues(obj: Record<string, any>, path = "") {
      for (const [key, val] of Object.entries(obj)) {
        const fullPath = path ? `${path}.${key}` : key;
        if (typeof val === "object" && val !== null) {
          checkValues(val, fullPath);
        } else {
          expect(typeof val).toBe("string");
          expect((val as string).length).toBeGreaterThan(0);
        }
      }
    }
    checkValues(zhCN);
  });

  it("all en values are non-empty strings", () => {
    function checkValues(obj: Record<string, any>, path = "") {
      for (const [key, val] of Object.entries(obj)) {
        const fullPath = path ? `${path}.${key}` : key;
        if (typeof val === "object" && val !== null) {
          checkValues(val, fullPath);
        } else {
          expect(typeof val).toBe("string");
          expect((val as string).length).toBeGreaterThan(0);
        }
      }
    }
    checkValues(en);
  });
});
