// @vitest-environment node
import { readFileSync } from "node:fs";
import { expect, it } from "vitest";
const css = readFileSync(new URL("./studio.css", import.meta.url), "utf8");
function tokens(selector: string) {
  const block = css.slice(css.indexOf(selector));
  return Object.fromEntries([...block.slice(0, block.indexOf("}")).matchAll(/--([a-z-]+):\s*(#[0-9a-f]{3,6})/g)].map((match) => [match[1], match[2]]));
}
function contrast(first: string, second: string) {
  const luminance = (hex: string) => {
    const text = hex.length === 4 ? hex.slice(1).split("").map((value) => value + value).join("") : hex.slice(1);
    const channels = [0, 2, 4].map((index) => parseInt(text.slice(index, index + 2), 16) / 255).map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
    return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
  };
  const values = [luminance(first), luminance(second)].sort((a, b) => b - a);
  return (values[0] + 0.05) / (values[1] + 0.05);
}
it("CSS defaults to dark and uses blue readable accents for both themes", () => {
  expect(css).toMatch(/^:root,\s*:root\[data-theme="dark"\]/);
  for (const selector of [':root[data-theme="dark"]', ':root[data-theme="light"]']) {
    const theme = tokens(selector);
    expect(contrast(theme.ink, theme.surface)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(theme.muted, theme.surface)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(theme.accent, theme["accent-soft"])).toBeGreaterThanOrEqual(4.5);
    expect(contrast(theme["accent-ink"], theme.accent)).toBeGreaterThanOrEqual(4.5);
    const blue = parseInt(theme.accent.slice(5, 7), 16);
    const red = parseInt(theme.accent.slice(1, 3), 16);
    expect(blue).toBeGreaterThan(red);
  }
});
