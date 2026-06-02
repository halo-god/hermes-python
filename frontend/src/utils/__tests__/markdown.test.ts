import { describe, it, expect, beforeEach } from "vitest";

describe("markdown renderer", () => {
  let renderMarkdown: typeof import("@/utils/markdown").renderMarkdown;

  beforeEach(async () => {
    const mod = await import("@/utils/markdown");
    renderMarkdown = mod.renderMarkdown;
  });

  it("renders basic paragraphs", () => {
    const html = renderMarkdown("Hello world");
    expect(html).toContain("Hello world");
    expect(html).toContain("<p>");
  });

  it("renders bold text", () => {
    const html = renderMarkdown("**bold**");
    expect(html).toContain("<strong>bold</strong>");
  });

  it("renders inline code", () => {
    const html = renderMarkdown("`code`");
    expect(html).toContain("<code>");
  });

  it("renders code blocks with language class", () => {
    const html = renderMarkdown("```python\nprint('hi')\n```");
    expect(html).toContain("language-python");
    expect(html).toContain("code-block-wrapper");
  });

  it("renders code copy button", () => {
    const html = renderMarkdown("```js\nconsole.log()\n```");
    expect(html).toContain("code-copy-btn");
  });

  it("renders links with target=_blank", () => {
    const html = renderMarkdown("[link](https://example.com)");
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener"');
  });

  it("renders tables", () => {
    const html = renderMarkdown("| A | B |\n|---|---|\n| 1 | 2 |");
    expect(html).toContain("<table>");
    expect(html).toContain("<td>");
  });

  it("renders headings", () => {
    const html = renderMarkdown("# Title\n## Subtitle");
    expect(html).toContain("<h1>");
    expect(html).toContain("<h2>");
  });

  it("renders blockquotes", () => {
    const html = renderMarkdown("> quote");
    expect(html).toContain("<blockquote>");
  });

  it("renders unordered lists", () => {
    const html = renderMarkdown("- item 1\n- item 2");
    expect(html).toContain("<ul>");
    expect(html).toContain("<li>");
  });

  it("handles empty input", () => {
    expect(renderMarkdown("")).toBe("");
    expect(renderMarkdown(null as any)).toBe("");
  });
});
