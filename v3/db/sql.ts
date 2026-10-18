/** Comment- and quote-aware helpers for the migration files. */

export function stripComments(sql: string): string {
  let out = "";
  let i = 0;
  while (i < sql.length) {
    if (sql[i] === "-" && sql[i + 1] === "-") {
      while (i < sql.length && sql[i] !== "\n") i++;
      continue;
    }
    if (sql[i] === "/" && sql[i + 1] === "*") {
      i += 2;
      while (i < sql.length && !(sql[i] === "*" && sql[i + 1] === "/")) i++;
      i = Math.min(sql.length, i + 2);
      continue;
    }
    if (sql[i] === "'") {
      const start = i;
      i++;
      while (i < sql.length) {
        if (sql[i] === "'" && sql[i + 1] === "'") {
          i += 2;
          continue;
        }
        if (sql[i] === "'") {
          i++;
          break;
        }
        i++;
      }
      out += sql.slice(start, i);
      continue;
    }
    const dollar = dollarQuoteAt(sql, i);
    if (dollar) {
      out += sql.slice(i, dollar.end);
      i = dollar.end;
      continue;
    }
    out += sql[i];
    i++;
  }
  return out;
}

/** Split a script into statements. Semicolons inside comments, strings, and dollar quotes stay put. */
export function splitSql(sql: string): string[] {
  const statements: string[] = [];
  let start = 0;
  let i = 0;
  while (i < sql.length) {
    if (sql[i] === "-" && sql[i + 1] === "-") {
      while (i < sql.length && sql[i] !== "\n") i++;
      continue;
    }
    if (sql[i] === "/" && sql[i + 1] === "*") {
      i += 2;
      while (i < sql.length && !(sql[i] === "*" && sql[i + 1] === "/")) i++;
      i = Math.min(sql.length, i + 2);
      continue;
    }
    if (sql[i] === "'") {
      i++;
      while (i < sql.length) {
        if (sql[i] === "'" && sql[i + 1] === "'") {
          i += 2;
          continue;
        }
        if (sql[i] === "'") {
          i++;
          break;
        }
        i++;
      }
      continue;
    }
    const dollar = dollarQuoteAt(sql, i);
    if (dollar) {
      i = dollar.end;
      continue;
    }
    if (sql[i] === ";") {
      let end = i + 1;
      let j = end;
      while (j < sql.length && (sql[j] === " " || sql[j] === "\t")) j++;
      // A same-line comment belongs to this statement, not the next one.
      if (sql[j] === "-" && sql[j + 1] === "-") {
        while (j < sql.length && sql[j] !== "\n") j++;
        end = j;
      }
      const comment = end > i + 1 ? sql.slice(i + 1, end) : "";
      pushStatement(statements, sql.slice(start, i) + comment);
      i = end;
      start = i;
      continue;
    }
    i++;
  }
  pushStatement(statements, sql.slice(start));
  return statements;
}

function pushStatement(statements: string[], raw: string): void {
  const statement = raw.trim();
  if (stripComments(statement).trim().length > 0) statements.push(statement);
}

function dollarQuoteAt(sql: string, i: number): { end: number } | null {
  if (sql[i] !== "$") return null;
  const tag = /^\$[A-Za-z0-9_]*\$/.exec(sql.slice(i));
  if (!tag) return null;
  const closer = tag[0];
  const end = sql.indexOf(closer, i + closer.length);
  if (end < 0) throw new Error("unterminated dollar quote");
  return { end: end + closer.length };
}
