"""Restore LaTeX backslashes that json.loads ate, turning them into raw control
chars in an already-decoded worked-solutions cache.

  0x08->\\b  0x09->\\t  0x0c->\\f   (always a LaTeX command here: \\binom \\times \\frac)
  0x0a->\\n  0x0d->\\r  ONLY when a lowercase letter follows (\\neq, \\right);
                        otherwise it was a real newline/CR -> collapse to a space.

Idempotent. Pass a cache path; prints what it changed."""
import json, sys
from pathlib import Path

CMD = {"\x08": "\\b", "\x09": "\\t", "\x0c": "\\f", "\x0a": "\\n", "\x0d": "\\r"}
AMBIG = {"\x0a", "\x0d"}  # could be a real newline instead of a command


def repair(s: str) -> str:
    out = []
    for j, ch in enumerate(s):
        if ch in CMD:
            after = s[j + 1] if j + 1 < len(s) else ""
            if ch in AMBIG and not ("a" <= after <= "z"):
                out.append(" ")            # genuine line break, not a \command
            else:
                out.append(CMD[ch])        # restore the LaTeX backslash
        else:
            out.append(ch)
    return out and "".join(out) or s


def main() -> None:
    path = Path(sys.argv[1])
    c = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for slug, rec in c.items():
        sol = rec.get("solution") or {}
        if not sol:
            continue
        touched = False
        fa = sol.get("final_answer")
        if isinstance(fa, str) and repair(fa) != fa:
            sol["final_answer"] = repair(fa); touched = True
        for st in sol.get("steps") or []:
            s = (st or {}).get("step")
            if isinstance(s, str) and repair(s) != s:
                st["step"] = repair(s); touched = True
            m = (st or {}).get("marks")
            if isinstance(m, str) and repair(m) != m:
                st["marks"] = repair(m); touched = True
        for k in ("ms_error",):
            v = sol.get(k)
            if isinstance(v, str) and repair(v) != v:
                sol[k] = repair(v); touched = True
        if touched:
            changed += 1
            print("  repaired", slug)
    path.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{changed} solutions repaired in {path.name}")


if __name__ == "__main__":
    main()
