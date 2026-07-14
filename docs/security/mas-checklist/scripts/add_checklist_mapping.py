#!/usr/bin/env python3
"""给分类 CSV 补 checklist 对齐列：masvs_control(具体控制项 ID) + control_title。
链路：test.weakness(MASWE) -> maswe.mappings.masvs-v2 -> masvs 控制项标题。"""
import os, re, glob, csv, subprocess

HERE = os.path.dirname(__file__)
CSV = os.path.join(HERE, "..", "data", "mas-static-classified.csv")
SCRATCH = ("/private/tmp/claude-501/-Users-zhouchunshi-Desktop-degate-app/"
           "0eb8b899-856c-428c-aea5-37b50778cf81/scratchpad/secscan")


def ensure(repo, url):
    d = os.path.join(SCRATCH, repo)
    if not os.path.isdir(d):
        d = os.path.join(HERE, "..", "data", "_" + repo)
        if not os.path.isdir(d):
            subprocess.run(["git", "clone", "--depth", "1", url, d], check=True)
    return d


def maswe_to_controls(maswe_dir):
    """MASWE-id -> [MASVS-XXX-N, ...]（masvs-v2 控制项）"""
    m = {}
    for f in glob.glob(os.path.join(maswe_dir, "**", "MASWE-*.md"), recursive=True):
        txt = open(f, encoding="utf-8").read()
        wid = re.search(r"^id:\s*(MASWE-\d+)", txt, re.M)
        v2 = re.search(r"masvs-v2:\s*\[([^\]]*)\]", txt)
        if wid and v2:
            ctrls = [c.strip() for c in v2.group(1).split(",") if c.strip()]
            m[wid.group(1)] = ctrls
    return m


def control_titles(masvs_dir):
    """MASVS-XXX-N -> 控制项标题（## Control 下一句）"""
    t = {}
    for f in glob.glob(os.path.join(masvs_dir, "controls", "MASVS-*.md")):
        txt = open(f, encoding="utf-8").read()
        cid = re.search(r"^#\s*(MASVS-[A-Z]+-\d+)", txt, re.M)
        ctrl = re.search(r"##\s*Control\s*\n+\s*(.+)", txt)
        if cid:
            t[cid.group(1)] = ctrl.group(1).strip() if ctrl else ""
    return t


def main():
    maswe_dir = ensure("maswe", "https://github.com/OWASP/maswe.git")
    masvs_dir = ensure("masvs", "https://github.com/OWASP/masvs.git")
    w2c = maswe_to_controls(maswe_dir)
    titles = control_titles(masvs_dir)

    with open(CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        ctrls = w2c.get(r["weakness"], [])
        # 只保留与本 test 所在 MASVS 大类一致的控制项优先；否则全列
        same_cat = [c for c in ctrls if c.split("-")[1] == r["masvs"]]
        chosen = same_cat or ctrls
        r["masvs_control"] = "; ".join(chosen)
        r["control_title"] = " / ".join(filter(None, (titles.get(c, "") for c in chosen)))

    fields = list(rows[0].keys())
    for c in ("masvs_control", "control_title"):
        if c not in fields:
            fields.append(c)
    with open(CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    mapped = sum(1 for r in rows if r["masvs_control"])
    print(f"补 checklist 对齐：{mapped}/{len(rows)} 行有 masvs_control")
    miss = [r["id"] for r in rows if not r["masvs_control"]]
    if miss:
        print(f"未映射（{len(miss)}）:", ", ".join(miss[:15]))


if __name__ == "__main__":
    main()
