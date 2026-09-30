import { Fragment, type ReactNode } from "react";

/** Minimal, dependency-free markdown renderer for the repo's own docs
 *  (headings, paragraphs, bullet lists, **bold**, `code`, [links](url)). */
function inline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    const t = m[0];
    if (t.startsWith("**")) parts.push(<strong key={k++}>{t.slice(2, -2)}</strong>);
    else if (t.startsWith("`")) parts.push(<code key={k++}>{t.slice(1, -1)}</code>);
    else {
      const mm = /\[([^\]]+)\]\(([^)]+)\)/.exec(t)!;
      parts.push(<a key={k++} href={mm[2]} target="_blank" rel="noreferrer">{mm[1]}</a>);
    }
    last = m.index + t.length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

export function Markdown({ source }: { source: string }) {
  const blocks: ReactNode[] = [];
  const lines = source.split("\n");
  let para: string[] = [];
  let list: string[] = [];
  let quote: string[] = [];
  const flush = () => {
    if (para.length) blocks.push(<p key={blocks.length}>{inline(para.join(" "))}</p>);
    if (list.length) blocks.push(<ul key={blocks.length}>{list.map((l, i) => <li key={i}>{inline(l)}</li>)}</ul>);
    if (quote.length) blocks.push(<blockquote key={blocks.length}>{inline(quote.join(" "))}</blockquote>);
    para = []; list = []; quote = [];
  };
  for (const raw of lines) {
    const l = raw.trimEnd();
    const h = /^(#{1,4})\s+(.*)/.exec(l);
    if (h) {
      flush();
      const lvl = Math.min(h[1].length + 1, 4);
      const Tag = (`h${lvl}` as unknown) as "h2";
      blocks.push(<Tag key={blocks.length}>{inline(h[2])}</Tag>);
    } else if (/^\s*[-*]\s+/.test(l)) {
      if (para.length) { const p = para; para = []; blocks.push(<p key={blocks.length}>{inline(p.join(" "))}</p>); }
      list.push(l.replace(/^\s*[-*]\s+/, ""));
    } else if (/^>\s?/.test(l)) {
      quote.push(l.replace(/^>\s?/, ""));
    } else if (l.trim() === "" || l.startsWith("```") || l.startsWith("---")) {
      flush();
    } else if (list.length && /^\s{2,}\S/.test(raw)) {
      list[list.length - 1] += " " + l.trim();
    } else {
      if (list.length) flush();
      para.push(l.trim());
    }
  }
  flush();
  return <div className="md">{blocks.map((b, i) => <Fragment key={i}>{b}</Fragment>)}</div>;
}
