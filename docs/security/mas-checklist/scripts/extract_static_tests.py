#!/usr/bin/env python3
"""解析 MASTG tests-beta/ frontmatter，过滤静态 test，输出 CSV。"""
import os, re, glob, csv, subprocess


def mastg_dir():
    d = os.environ.get(
        "MASTG_DIR",
        "/private/tmp/claude-501/-Users-zhouchunshi-Desktop-degate-app/"
        "0eb8b899-856c-428c-aea5-37b50778cf81/scratchpad/secscan/mastg",
    )
    if not os.path.isdir(os.path.join(d, "tests-beta")):
        d = os.path.join(os.path.dirname(__file__), "..", "data", "_mastg")
        if not os.path.isdir(os.path.join(d, "tests-beta")):
            subprocess.run(
                ["git", "clone", "--depth", "1",
                 "https://github.com/OWASP/mastg.git", d],
                check=True,
            )
    return d


def parse_fm(text):
    m = re.search(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return None
    fm = m.group(1)

    def g(k):
        mm = re.search(rf"^{k}:\s*(.+)$", fm, re.M)
        return mm.group(1).strip() if mm else ""

    return g


def main():
    base = os.path.join(mastg_dir(), "tests-beta")
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "mas-static-tests.csv")
    rows = []
    for f in glob.glob(os.path.join(base, "**", "*.md"), recursive=True):
        g = parse_fm(open(f, encoding="utf-8").read())
        if not g:
            continue
        typ = g("type")
        if "static" not in typ:  # 只要静态
            continue
        pm = re.search(r"MASVS-([A-Z]+)", f)
        rows.append({
            "id": g("id"), "platform": g("platform"),
            "masvs": pm.group(1) if pm else "?",
            "type": typ, "profiles": g("profiles"),
            "has_manual": "yes" if "manual" in typ else "no",
            "weakness": g("weakness"), "title": g("title"),
        })
    rows.sort(key=lambda r: (r["platform"], r["masvs"], r["id"]))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"写出 {len(rows)} 个静态 test → {out_path}")


if __name__ == "__main__":
    main()
