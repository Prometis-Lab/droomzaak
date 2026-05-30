import { Fragment, type ReactNode } from "react";

/** Minimal, dependency-free markdown for the agent's chat replies.
 *
 *  Handles the realistic subset the agent emits — paragraphs with soft line
 *  breaks, bullet/numbered lists, **bold**, and [label](url) links — so a
 *  multi-item summary (e.g. the chapter-4 permit/subsidy/legal cards) reads as a
 *  scannable list instead of a flat text dump.
 *
 *  Security: builds React elements only (never dangerouslySetInnerHTML), so all
 *  text is auto-escaped. Links are restricted to http(s) — a non-web scheme
 *  (e.g. javascript:) is dropped to its label text. Reply text is model-sourced.
 */

const SAFE_URL = /^https?:\/\//i;
const INLINE = /\*\*([^*]+)\*\*|\[([^\]]+)\]\(([^)]+)\)/g;
const BULLET = /^\s*[-*]\s+/;
const NUMBERED = /^\s*\d+\.\s+/;
const HEADING = /^#{1,6}\s+/;

function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let last = 0;
  let key = 0;
  let m: RegExpExecArray | null;
  INLINE.lastIndex = 0;
  while ((m = INLINE.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index));
    if (m[1] !== undefined) {
      nodes.push(<strong key={key++}>{m[1]}</strong>);
    } else if (SAFE_URL.test(m[3])) {
      nodes.push(
        <a key={key++} href={m[3]} target="_blank" rel="noreferrer">{m[2]}</a>,
      );
    } else {
      nodes.push(m[2]); // unsafe scheme → keep the label, drop the link
    }
    last = INLINE.lastIndex;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

export function ChatMarkdown({ text }: { text: string }) {
  const blocks = text
    .replace(/\r\n/g, "\n")
    .split(/\n{2,}/)
    .map((b) => b.trim())
    .filter(Boolean);

  return (
    <>
      {blocks.map((block, bi) => {
        const lines = block.split("\n");
        if (lines.every((l) => BULLET.test(l))) {
          return (
            <ul key={bi} className="chat-md-list">
              {lines.map((l, i) => <li key={i}>{renderInline(l.replace(BULLET, ""))}</li>)}
            </ul>
          );
        }
        if (lines.every((l) => NUMBERED.test(l))) {
          return (
            <ol key={bi} className="chat-md-list">
              {lines.map((l, i) => <li key={i}>{renderInline(l.replace(NUMBERED, ""))}</li>)}
            </ol>
          );
        }
        return (
          <p key={bi}>
            {lines.map((l, i) => (
              <Fragment key={i}>
                {i > 0 && <br />}
                {renderInline(l.replace(HEADING, ""))}
              </Fragment>
            ))}
          </p>
        );
      })}
    </>
  );
}
