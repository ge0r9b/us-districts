#!/usr/bin/env python3
"""Q-E12: insert the boundary_set column right after retrieved_at (column 14) in existing bot-row CSVs (.csv or .csv.gz).
The 13 original columns stay unchanged and in order; an optional method column moves to column 15. Idempotent: a file
that already has boundary_set is left alone. .gz files are rewritten with gzip level 9, mtime 0 (same as the writers).
Values: lowercase with hyphens, e.g. v2-2024, tiger-2020, v2-2016-precincts.
usage: add_boundary_set.py <boundary_set> <file>..."""
import sys, csv, io, gzip
val, files = sys.argv[1], sys.argv[2:]
for f in files:
    raw = open(f, 'rb').read(); gz = f.endswith('.gz'); t = (gzip.decompress(raw) if gz else raw).decode('utf-8')
    lt = '\r\n' if '\r\n' in t else '\n'   # keep the file's own line endings (the 2016 FEC and PA files are CRLF)
    rows = list(csv.reader(io.StringIO(t, newline='')))
    if 'boundary_set' in rows[0]: print('skip', f); continue
    i = rows[0].index('retrieved_at') + 1; assert i == 13, (f, rows[0])
    out = [r[:i] + ['boundary_set' if n == 0 else val] + r[i:] for n, r in enumerate(rows)]
    b = io.StringIO(); csv.writer(b, lineterminator=lt).writerows(out); s = b.getvalue().encode('utf-8')
    # round-trip check: dropping the new column gives back the original bytes
    b2 = io.StringIO(); csv.writer(b2, lineterminator=lt).writerows(rows)
    assert b2.getvalue() == t, f'{f}: csv round-trip would change other bytes'
    open(f, 'wb').write(gzip.compress(s, 9, mtime=0) if gz else s)
    print(f, len(rows) - 1)
