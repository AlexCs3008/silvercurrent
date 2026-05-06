/**
 * Pure helpers for parsing and rendering Deal Sheet markdown.
 *
 * Lifted out of `deal-sheet-view.tsx` so the compare page can reuse the same
 * section split without duplicating logic. The Analyst writes Deal Sheets
 * with a fixed seven-section structure starting with `### Snapshot`.
 */

export type DealSheetSection = {
  title: string;
  body: string;
};

/**
 * Split markdown on `### ` headers. Content before the first header is
 * dropped (the Analyst's prompt locks the structure to start with `### Snapshot`).
 */
export function parseDealSheetSections(markdown: string): DealSheetSection[] {
  const sections: DealSheetSection[] = [];
  const lines = markdown.split(/\r?\n/);
  let currentTitle: string | null = null;
  let currentBody: string[] = [];

  function flush() {
    if (currentTitle !== null) {
      sections.push({ title: currentTitle, body: currentBody.join("\n") });
    }
  }

  for (const line of lines) {
    const m = /^###\s+(.+)$/.exec(line);
    if (m) {
      flush();
      currentTitle = m[1].trim();
      currentBody = [];
    } else if (currentTitle !== null) {
      currentBody.push(line);
    }
  }
  flush();
  return sections;
}

/**
 * Render `**bold**` → `<strong>`. Escapes the rest so `dangerouslySetInnerHTML`
 * stays safe: the only produced HTML is `<strong>` from a regex applied to
 * already-escaped text.
 */
export function renderBoldOnly(text: string): string {
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
  return escaped.replace(
    /\*\*([^*]+?)\*\*/g,
    '<strong class="font-semibold">$1</strong>',
  );
}
