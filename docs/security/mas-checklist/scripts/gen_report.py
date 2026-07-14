#!/usr/bin/env python3
"""读分类 CSV，生成 MAS Checklist 静态检查自动化分类报告（Markdown）。"""
import os, csv
from collections import Counter, defaultdict

HERE = os.path.dirname(__file__)
CSV = os.path.join(HERE, "..", "data", "mas-static-classified.csv")
OUT = os.path.join(HERE, "..", "MAS-Checklist-Static-Classification.md")

READY_LABEL = {"yes": "✅ 现成规则", "partial": "🟡 部分/需人工确认", "no": "🔴 需自建/专用工具"}


def load():
    with open(CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def overview(rows):
    out = ["## 总览\n"]
    out.append(f"MASTG v2 共 201 个 test，其中**静态 test {len(rows)} 个**（Android "
              f"{sum(r['platform']=='android' for r in rows)} / iOS "
              f"{sum(r['platform']=='ios' for r in rows)}），覆盖全部 8 个 MASVS 组。"
              f"**只针对原生代码（Swift/ObjC/Java/Kotlin），Dart 业务代码不在范围。**\n")
    out.append("| 平台 | ✅ 现成规则 | 🟡 部分 | 🔴 需自建 | 小计 |")
    out.append("|---|---|---|---|---|")
    for plat in ("android", "ios"):
        pr = [r for r in rows if r["platform"] == plat]
        c = Counter(r["ready_rule"] for r in pr)
        out.append(f"| {plat} | {c['yes']} | {c['partial']} | {c['no']} | {len(pr)} |")
    c = Counter(r["ready_rule"] for r in rows)
    out.append(f"| **合计** | **{c['yes']}** | **{c['partial']}** | **{c['no']}** | **{len(rows)}** |")
    tier = Counter(r["tier"] for r in rows)
    out.append(f"\n档位：可自动（纯静态）**{tier['auto']}**，半自动（含 manual、工具初筛+人工确认）**{tier['semi']}**。\n")
    out.append("**一句话结论**：静态原生检查里，"
               f"{c['yes']}/{len(rows)} 已有现成规则可直接进 CI，{c['partial']} 有工具但需人工确认"
               f"（iOS ObjC 占多数，因 semgrep 不支持 ObjC 只能 libsast 正则），"
               f"{c['no']} 属二进制/SCA 类、需专用工具而非 semgrep。\n")
    return "\n".join(out)


def platform_table(rows, plat):
    """按 checklist 控制项（MASVS control）分组，读起来就像 checklist。"""
    from collections import OrderedDict
    pr = [r for r in rows if r["platform"] == plat]
    groups = OrderedDict()
    for r in sorted(pr, key=lambda r: (r["masvs"], r["masvs_control"], r["id"])):
        groups.setdefault((r["masvs_control"], r["control_title"]), []).append(r)
    out = [f"## {plat.upper()} 分类明细（{len(pr)} 条，按 checklist 控制项分组）\n"]
    for (ctrl, title), items in groups.items():
        out.append(f"\n### ☑️ {ctrl} — {title[:90]}")
        out.append("| TEST | 档位 | 现成规则 | 说明 |")
        out.append("|---|---|---|---|")
        for r in items:
            note = r["gap_note"] or ("mobsfscan/MASTG 规则覆盖" if r["ready_rule"] == "yes" else "")
            out.append(f"| {r['id']} | {r['tier']} | {READY_LABEL[r['ready_rule']]} "
                       f"| {r['title'][:42]}{'…' if len(r['title'])>42 else ''} |")
    return "\n".join(out)


def non_automatable(rows):
    out = ["## 不可自动化 / 需专用工具的静态项（🔴 no）+ 替代方案\n"]
    nos = [r for r in rows if r["ready_rule"] == "no"]
    groups = defaultdict(list)
    for r in nos:
        t = r["title"].lower()
        if any(k in t for k in ("pic", "canary", "stack", "position independent")):
            groups["二进制编译加固标志（PIC / Stack Canary）"].append(r)
        elif any(k in t for k in ("symbol", "obfusc", "sign", "strip", "debug symbol")):
            groups["二进制签名 / 符号表 / 混淆度"].append(r)
        else:
            groups["依赖漏洞 / 追踪域名（SCA 类）"].append(r)
    alt = {
        "二进制编译加固标志（PIC / Stack Canary）":
            "语义扫描无法判定编译产物属性。替代：`checksec` / `radare2` 对成品二进制静态核验，接进 CI 的构建后步骤。",
        "二进制签名 / 符号表 / 混淆度":
            "同属编译产物属性。替代：`radare2` / `otool` / `nm` 脚本检查符号剥离与签名，构建后跑。",
        "依赖漏洞 / 追踪域名（SCA 类）":
            "属软件成分分析，非代码模式。替代：`osv-scanner` / GitHub Dependabot（原生依赖）+ 追踪域名黑名单比对脚本。",
    }
    for g, items in groups.items():
        out.append(f"### {g}")
        out.append("、".join(f"`{r['id']}`({r['platform']})" for r in items))
        out.append(f"\n**替代方案**：{alt[g]}\n")
    out.append("> 这些项虽不能用 semgrep 补规则，但对应工具都是 **CLI、可进 CI**，只是属于二进制/SCA 轨道而非源码 SAST 轨道。\n")
    return "\n".join(out)


def ci_section():
    return """## GitHub Actions 可行性小结

**结论：静态原生检查几乎全部可进 GitHub CI**，且比动态测试简单——SAST 容器化、普通 `ubuntu-latest` runner 即可，**不需要 emulator / 真机**。

- **✅ 现成规则（65 条）**：`semgrep`（MASTG rules + p/java/p/kotlin）+ `mobsfscan` 直接跑，SARIF 上报 GitHub code scanning。
- **🟡 部分（62 条，多为 iOS ObjC）**：`mobsfscan`（libsast 正则）跑得动，findings 作为 PR 初筛，人工在 PR 复核（半自动的"人工 gate"）。
- **🔴 需专用工具（16 条）**：二进制类走 `radare2`/`checksec`（构建后步骤）、SCA 走 `osv-scanner`/Dependabot——都是 CLI，同样可进 CI，只是独立 job。

**工程注意（来自 P0 实测）**：
- `mobsfscan` 多路径有 bug，需**逐目录跑再聚合**。
- `semgrep` 多目标在 CI 用 bash（非 zsh），无需 `${=DIRS}` 分词技巧。
- diff-aware：`SEMGREP_BASELINE_REF` 只报 PR 新增，避免存量淹没。
- 半自动项在 CI 只做初筛，最终判定 + 误报排除仍需人工（见 MASTG 验证机制：工具取证、人下判决）。

workflow 骨架见同目录 `github-actions-blueprint.yml`（蓝图，未接入运行）。
"""


def main():
    rows = load()
    parts = [
        "# MAS Checklist 静态检查自动化分类报告\n",
        "> 范围：MASTG v2 静态 test × 原生代码（Swift/ObjC/Java/Kotlin）。Dart 不在范围。数据源 `data/mas-static-classified.csv`。\n",
        overview(rows),
        non_automatable(rows),
        ci_section(),
        platform_table(rows, "android"),
        platform_table(rows, "ios"),
    ]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n\n".join(parts))
    print(f"报告写出 → {OUT}（{len(rows)} 条）")


if __name__ == "__main__":
    main()
