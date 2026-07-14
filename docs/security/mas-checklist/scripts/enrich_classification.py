#!/usr/bin/env python3
"""按 rubric 给静态 test 加 tier / base_tool / ci_feasible 列。"""
import os, csv

HERE = os.path.dirname(__file__)
IN = os.path.join(HERE, "..", "data", "mas-static-tests.csv")
OUT = os.path.join(HERE, "..", "data", "mas-static-classified.csv")


def base_tool(platform, masvs):
    if platform == "android":
        return "mobsfscan + MASTG semgrep 规则 + p/java/p/kotlin"
    if platform == "ios":
        return "mobsfscan + akabe1/insideapp(Swift); ObjC 走 mobsfscan libsast"
    return "mobsfscan(通用/config)"


def main():
    with open(IN, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["tier"] = "semi" if r["has_manual"] == "yes" else "auto"
        r["base_tool"] = base_tool(r["platform"], r["masvs"])
        # 静态 + 有 CLI 工具即 CI 可行；Dart 缺口在 annotate 阶段覆盖，这里先全 yes
        r["ci_feasible"] = "yes"
    fields = list(rows[0].keys())
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"富化 {len(rows)} 行 → {OUT}")


if __name__ == "__main__":
    main()
