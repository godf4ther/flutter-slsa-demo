# MAS Checklist 静态检查自动化分类 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 MASTG v2 的 143 个静态 test 逐条分类（可自动 / 半自动 / 待自建），Android/iOS 分表，标注具体工具与 GitHub CI 可行性，并给出不可自动项的替代方案与 workflow 蓝图。

**Architecture:** 数据驱动 + 人工富化。脚本从本地 MASTG `tests-beta/` YAML 提取客观字段（platform/type/profiles/MASVS）→ 脚本按 rubric 机械富化档位与基础工具 → 人工过一遍现成规则匹配与 Dart/ObjC 缺口 → 汇总成分类报告 + CI 可行性小结 + workflow 蓝图。产出为文档，不运维真实 CI。

**Tech Stack:** Python 3（标准库，解析 YAML frontmatter 用正则，避免额外依赖）、semgrep/mobsfscan（仅引用，不在本计划内运行）、Markdown。

## Global Constraints

- 范围仅**静态**：只处理 `type` 含 `static` 的 test，排除全部纯动态 test。
- **不搭真实 CI**：GitHub Actions 部分只产出蓝图（`.yml` 示例 + 可行性结论），不接入运行。
- **Android / iOS 全程分开**成表。
- 全量 143 个静态 test 都要分类，保留 `profiles`(L1/L2/R/P) 标注。
- 数据源权威值（脚本自检必须命中）：**静态 test 共 143**（Android 79 = 纯 static 55 + static+manual 24；iOS 64 = 纯 static 31 + static+manual 33）。
- MASTG 源目录：环境变量 `MASTG_DIR`，默认 `/private/tmp/claude-501/-Users-zhouchunshi-Desktop-degate-app/0eb8b899-856c-428c-aea5-37b50778cf81/scratchpad/secscan/mastg`；若不存在则 `git clone --depth 1 https://github.com/OWASP/mastg.git`。
- **默认不自动 git commit（用户偏好）**：各任务末尾的 commit 步骤为建议，执行时先 `git add` 暂存并由用户确认后再提交。
- 工具映射基线（来自 spec §3，供各任务引用）：
  - Android Java/Kotlin → MASTG 52 条 semgrep 规则 + mobsfscan + `p/java`/`p/kotlin`（P0 已验证）
  - iOS Swift → mobsfscan + akabe1/insideapp 社区规则
  - iOS Objective-C → mobsfscan（libsast 正则；semgrep 不支持 ObjC）
  - Dart（`lib/` 主体）→ 自写 experimental semgrep 规则（无现成规则）
  - Manifest/plist/config → mobsfscan + MASTG config 规则

---

### Task 1: 静态 test 提取脚本

从 MASTG `tests-beta/` 解析所有 test 的 frontmatter，过滤出静态 test，输出结构化 CSV。

**Files:**
- Create: `docs/security/mas-checklist/scripts/extract_static_tests.py`
- Create（脚本产物）: `docs/security/mas-checklist/data/mas-static-tests.csv`
- Test: `docs/security/mas-checklist/scripts/test_extract.py`

**Interfaces:**
- Produces: `mas-static-tests.csv`，列 = `id,platform,masvs,type,profiles,has_manual,weakness,title`。每行一个静态 test。供 Task 2 消费。

- [ ] **Step 1: 写失败测试**

`docs/security/mas-checklist/scripts/test_extract.py`：
```python
import subprocess, csv, os, sys
HERE = os.path.dirname(__file__)

def run_and_load():
    subprocess.run([sys.executable, os.path.join(HERE, "extract_static_tests.py")], check=True)
    with open(os.path.join(HERE, "..", "data", "mas-static-tests.csv"), encoding="utf-8") as f:
        return list(csv.DictReader(f))

def test_counts():
    rows = run_and_load()
    assert len(rows) == 143, f"期望 143 静态 test，实际 {len(rows)}"
    android = [r for r in rows if r["platform"] == "android"]
    ios = [r for r in rows if r["platform"] == "ios"]
    assert len(android) == 79, f"Android 期望 79，实际 {len(android)}"
    assert len(ios) == 64, f"iOS 期望 64，实际 {len(ios)}"
    # 每行必须有非空 id / masvs / type
    for r in rows:
        assert r["id"] and r["masvs"] and r["type"], f"字段缺失: {r}"
    # 所有行都是静态
    assert all("static" in r["type"] for r in rows)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd docs/security/mas-checklist/scripts && python3 -m pytest test_extract.py -v`
Expected: FAIL（`extract_static_tests.py` 不存在 / CSV 未生成）

- [ ] **Step 3: 写脚本**

`docs/security/mas-checklist/scripts/extract_static_tests.py`：
```python
#!/usr/bin/env python3
"""解析 MASTG tests-beta/ frontmatter，过滤静态 test，输出 CSV。"""
import os, re, glob, csv, subprocess, sys

def mastg_dir():
    d = os.environ.get("MASTG_DIR",
        "/private/tmp/claude-501/-Users-zhouchunshi-Desktop-degate-app/"
        "0eb8b899-856c-428c-aea5-37b50778cf81/scratchpad/secscan/mastg")
    if not os.path.isdir(os.path.join(d, "tests-beta")):
        d = os.path.join(os.path.dirname(__file__), "..", "data", "_mastg")
        if not os.path.isdir(os.path.join(d, "tests-beta")):
            subprocess.run(["git", "clone", "--depth", "1",
                            "https://github.com/OWASP/mastg.git", d], check=True)
    return d

def parse_fm(text):
    m = re.search(r'^---\n(.*?)\n---', text, re.S)
    if not m: return None
    fm = m.group(1)
    def g(k):
        mm = re.search(rf'^{k}:\s*(.+)$', fm, re.M)
        return mm.group(1).strip() if mm else ""
    return g

def main():
    base = os.path.join(mastg_dir(), "tests-beta")
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "mas-static-tests.csv")
    rows = []
    for f in glob.glob(os.path.join(base, "**", "*.md"), recursive=True):
        g = parse_fm(open(f, encoding="utf-8").read())
        if not g: continue
        typ = g("type")
        if "static" not in typ:      # 只要静态
            continue
        pm = re.search(r'MASVS-([A-Z]+)', f)
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
        w.writeheader(); w.writerows(rows)
    print(f"写出 {len(rows)} 个静态 test → {out_path}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd docs/security/mas-checklist/scripts && python3 -m pytest test_extract.py -v`
Expected: PASS（143 / 79 / 64 全部命中）

- [ ] **Step 5: 暂存（提交由用户确认）**

```bash
git add docs/security/mas-checklist/scripts/extract_static_tests.py \
        docs/security/mas-checklist/scripts/test_extract.py \
        docs/security/mas-checklist/data/mas-static-tests.csv
# 用户确认后: git commit -m "feat(sec): MASTG 静态 test 提取脚本"
```

---

### Task 2: 档位 + 基础工具 + CI 可行性富化脚本

按 rubric 机械地给每个静态 test 加三列：自动化档位、基础工具、CI 可行性。

**Files:**
- Create: `docs/security/mas-checklist/scripts/enrich_classification.py`
- Create（产物）: `docs/security/mas-checklist/data/mas-static-classified.csv`
- Test: `docs/security/mas-checklist/scripts/test_enrich.py`

**Interfaces:**
- Consumes: `mas-static-tests.csv`（Task 1）
- Produces: `mas-static-classified.csv`，在 Task 1 列基础上新增 `tier`(auto|semi)、`base_tool`(字符串)、`ci_feasible`(yes|needs_custom_rule)。供 Task 3 消费。

- [ ] **Step 1: 写失败测试**

`docs/security/mas-checklist/scripts/test_enrich.py`：
```python
import subprocess, csv, os, sys
HERE = os.path.dirname(__file__)

def run_and_load():
    subprocess.run([sys.executable, os.path.join(HERE, "extract_static_tests.py")], check=True)
    subprocess.run([sys.executable, os.path.join(HERE, "enrich_classification.py")], check=True)
    with open(os.path.join(HERE, "..", "data", "mas-static-classified.csv"), encoding="utf-8") as f:
        return list(csv.DictReader(f))

def test_enrichment_complete():
    rows = run_and_load()
    assert len(rows) == 143
    for r in rows:
        # 档位由 has_manual 决定
        assert r["tier"] == ("semi" if r["has_manual"] == "yes" else "auto"), r["id"]
        # 每行都有非空 base_tool 和 ci_feasible
        assert r["base_tool"], f"{r['id']} 缺 base_tool"
        assert r["ci_feasible"] in ("yes", "needs_custom_rule"), r["id"]
    # 纯 auto 应占多数（55+31=86）
    assert sum(1 for r in rows if r["tier"] == "auto") == 86
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd docs/security/mas-checklist/scripts && python3 -m pytest test_enrich.py -v`
Expected: FAIL（`enrich_classification.py` 不存在）

- [ ] **Step 3: 写脚本**

`docs/security/mas-checklist/scripts/enrich_classification.py`：
```python
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
        # 静态 + 有 CLI 工具即 CI 可行；Dart 缺口在 Task 3 覆盖，这里先全 yes
        r["ci_feasible"] = "yes"
    fields = list(rows[0].keys())
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    print(f"富化 {len(rows)} 行 → {OUT}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd docs/security/mas-checklist/scripts && python3 -m pytest test_enrich.py -v`
Expected: PASS

- [ ] **Step 5: 暂存**

```bash
git add docs/security/mas-checklist/scripts/enrich_classification.py \
        docs/security/mas-checklist/scripts/test_enrich.py \
        docs/security/mas-checklist/data/mas-static-classified.csv
# 用户确认后 commit
```

---

### Task 3: 现成规则匹配 + Dart/ObjC 缺口人工标注

这是核心判断环节：给每个可自动项标"现成规则有无"，并识别 Flutter 特有缺口（app 逻辑在 Dart、无现成规则）与 iOS ObjC 缺口，落成两新列。此步是**人工逐条过**（143 行），不强套脚本。

**Files:**
- Modify: `docs/security/mas-checklist/data/mas-static-classified.csv`（新增列 `ready_rule`、`gap_note`）
- Create: `docs/security/mas-checklist/scripts/annotate_gaps.py`（承载人工判定结果的映射表，可复现）
- Test: `docs/security/mas-checklist/scripts/test_annotate.py`

**Interfaces:**
- Consumes: `mas-static-classified.csv`（Task 2）
- Produces: 同文件新增 `ready_rule`(yes|no|partial)、`gap_note`(空或说明)。规则匹配依据：MASTG `rules/` 52 条按 `mastg-android-<topic>` 命名可与 android test 主题对应；iOS ObjC 一律 partial（libsast 粗）；涉及 app 业务逻辑(在 Dart)的 STORAGE/CRYPTO/NETWORK/CODE test 标 gap="Dart 层需自写规则"。

- [ ] **Step 1: 写失败测试**

`docs/security/mas-checklist/scripts/test_annotate.py`：
```python
import subprocess, csv, os, sys
HERE = os.path.dirname(__file__)

def load():
    for s in ("extract_static_tests.py","enrich_classification.py","annotate_gaps.py"):
        subprocess.run([sys.executable, os.path.join(HERE, s)], check=True)
    with open(os.path.join(HERE,"..","data","mas-static-classified.csv"),encoding="utf-8") as f:
        return list(csv.DictReader(f))

def test_no_unclassified():
    rows = load()
    for r in rows:
        assert r.get("ready_rule") in ("yes","no","partial"), f"{r['id']} ready_rule 未定"
        # ready_rule=no 的 auto 项必须有 gap_note（说明为何没现成规则+替代）
        if r["ready_rule"] == "no":
            assert r.get("gap_note"), f"{r['id']} 标 no 但无 gap_note"
    # ci_feasible 需据 Dart 缺口更新：Dart 自写类应为 needs_custom_rule
    assert any(r["ci_feasible"] == "needs_custom_rule" for r in rows)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd docs/security/mas-checklist/scripts && python3 -m pytest test_annotate.py -v`
Expected: FAIL（`annotate_gaps.py` 不存在）

- [ ] **Step 3: 人工判定并写映射脚本**

先人工过一遍 143 行（对照 MASTG `rules/` 规则名清单 + spec §3 工具映射 + P0 实测覆盖），产出判定映射，写入 `annotate_gaps.py`。脚本结构：
```python
#!/usr/bin/env python3
"""承载 Task 3 人工判定：现成规则有无 + Dart/ObjC 缺口。"""
import os, csv
HERE = os.path.dirname(__file__)
CSV = os.path.join(HERE, "..", "data", "mas-static-classified.csv")

# 人工判定结果：test id -> (ready_rule, gap_note, ci_override)
# 判定依据（在此逐条填全，示例见下，实施时补齐 143 行相关项）：
#  - android 主题能对应 MASTG rules/ 某条 → ready_rule=yes
#  - iOS ObjC-only 主题 → partial（libsast 粗匹配）
#  - app 业务逻辑落在 Dart 的 STORAGE/CRYPTO/NETWORK/CODE → no + "Dart 层需自写规则" + ci=needs_custom_rule
JUDGMENTS = {
    # 示例（实施时以真实 test id 填全）：
    # "MASTG-TEST-0215": ("yes", "", ""),                # iOS backup 排除，mobsfscan 有
    # "MASTG-TEST-0xxx": ("no", "Dart 层需自写规则", "needs_custom_rule"),
}
DEFAULT = ("partial", "无精确现成规则，可用通用 SAST 初筛后人工确认", "")

def main():
    with open(CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        rr, note, ci = JUDGMENTS.get(r["id"], DEFAULT)
        r["ready_rule"] = rr
        r["gap_note"] = note
        if ci:
            r["ci_feasible"] = ci
    fields = list(rows[0].keys())
    for c in ("ready_rule","gap_note"):
        if c not in fields: fields.append(c)
    with open(CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    print(f"标注 {len(rows)} 行")

if __name__ == "__main__":
    main()
```
实施要求：把 `JUDGMENTS` 补全到覆盖所有需要非 DEFAULT 判定的 test（尤其 Dart 缺口项与 android 有现成规则项），使 test_annotate 通过。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd docs/security/mas-checklist/scripts && python3 -m pytest test_annotate.py -v`
Expected: PASS

- [ ] **Step 5: 暂存**

```bash
git add docs/security/mas-checklist/scripts/annotate_gaps.py \
        docs/security/mas-checklist/scripts/test_annotate.py \
        docs/security/mas-checklist/data/mas-static-classified.csv
# 用户确认后 commit
```

---

### Task 4: 不可自动化项 + 替代方案章节

从分类数据里挑出 `ready_rule=no` 或 `ci_feasible=needs_custom_rule` 或半自动本质人工的项，成文替代方案。

**Files:**
- Create: `docs/security/mas-checklist/sections/04-non-automatable.md`

**Interfaces:**
- Consumes: `mas-static-classified.csv`（Task 3 完整版）

- [ ] **Step 1: 生成候选清单**

Run: `cd docs/security/mas-checklist && python3 -c "import csv; rows=list(csv.DictReader(open('data/mas-static-classified.csv'))); [print(r['platform'],r['id'],r['masvs'],r['ready_rule'],r['gap_note']) for r in rows if r['ready_rule']!='yes']"`
Expected: 打印所有非 `yes` 的 test（人工替代方案的输入）

- [ ] **Step 2: 写章节**

`sections/04-non-automatable.md`，按缺口类型分组，每组给替代方案：
```markdown
## 不可自动化 / 待自建的静态项与替代方案

### A. Dart 层业务逻辑（无现成规则 → 自写）
[列出 STORAGE/CRYPTO/NETWORK/CODE 中落在 Dart 的 test，替代方案：自写 experimental semgrep Dart 规则，给 2-3 条 PoC 规则示例]

### B. iOS Objective-C（semgrep 不支持 → libsast/手动）
[列出 ObjC-only 主题 test，替代方案：mobsfscan libsast 正则初筛 + 人工复核]

### C. 本质人工代码审查的 static+manual 项
[列出需人读判定的 test，替代方案：审查清单化 + 在 PR 模板加 sign-off]
```

- [ ] **Step 3: 自检**

确认每个 Task 3 标非 `yes` 的 test 在本章节 A/B/C 之一有归属且有替代方案。无遗漏。

- [ ] **Step 4: 暂存**

```bash
git add docs/security/mas-checklist/sections/04-non-automatable.md
# 用户确认后 commit
```

---

### Task 5: GitHub Actions 可行性小结 + workflow 蓝图

**Files:**
- Create: `docs/security/mas-checklist/sections/05-ci-feasibility.md`
- Create: `docs/security/mas-checklist/github-actions-blueprint.yml`（示例，不接入运行）

**Interfaces:**
- Consumes: 分类数据 + spec §3 工具映射

- [ ] **Step 1: 写 workflow 蓝图**

`github-actions-blueprint.yml`（注释说明这是蓝图、未接入）：
```yaml
# 蓝图 — MAS Checklist 静态检查在 GitHub Actions 的可行形态（未接入运行）
name: mas-static-scan
on: [pull_request]
jobs:
  static-scan:
    runs-on: ubuntu-latest        # 静态无需 emulator，普通 runner 即可
    steps:
      - uses: actions/checkout@v4
      - name: Install scanners
        run: pipx install semgrep mobsfscan
      - name: Secrets + generic
        run: semgrep scan --config p/secrets --metrics=off --sarif -o secrets.sarif lib packages
      - name: Android native (MASTG + registry)
        run: |
          git clone --depth 1 https://github.com/OWASP/mastg /tmp/mastg
          DIRS="android $(find packages -type d -name android -not -path '*/example/*' | tr '\n' ' ')"
          semgrep scan --config /tmp/mastg/rules --config p/java --config p/kotlin \
            --metrics=off --sarif -o android.sarif ${DIRS}     # 注意 CI 若用 bash 无需 ${=DIRS}
      - name: iOS + Dart (mobsfscan + 自写规则)
        run: |
          mobsfscan --sarif -o ios.sarif packages || true       # exit=1=有发现
          semgrep scan --config docs/security/rules/dart --metrics=off --sarif -o dart.sarif lib || true
      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: . }
```

- [ ] **Step 2: 写可行性小结**

`sections/05-ci-feasibility.md`：覆盖——静态项容器化无需 emulator（对比动态需 emulator）、diff-aware（`SEMGREP_BASELINE_REF` 只报新增）、SARIF 进 GitHub code scanning、逐目录/zsh-vs-bash 分词坑（引用 P0 经验）、各工具 runner 需求、以及"半自动项在 CI 做初筛、人工 gate 在 PR 复核"的定位。

- [ ] **Step 3: 自检**

确认蓝图里每个 step 对应到分类矩阵的一类工具，且明确标注"未接入运行"。

- [ ] **Step 4: 暂存**

```bash
git add docs/security/mas-checklist/sections/05-ci-feasibility.md \
        docs/security/mas-checklist/github-actions-blueprint.yml
# 用户确认后 commit
```

---

### Task 6: 汇总交付文档 + Artifact

把数据与各章节汇总成一份人读报告，并发布 Artifact。

**Files:**
- Create: `docs/security/mas-checklist/MAS-Checklist-Static-Classification.md`
- Create: `docs/security/mas-checklist/report.html`（Artifact 源）
- Test: `docs/security/mas-checklist/scripts/test_report.py`

**Interfaces:**
- Consumes: `mas-static-classified.csv` + `sections/04` + `sections/05`

- [ ] **Step 1: 写报告生成脚本 + 失败测试**

脚本 `scripts/gen_report.py` 读 CSV，生成总览统计（每平台 auto/semi 计数、ready_rule 分布）+ Android/iOS 两张分类表（Markdown），拼接 §4/§5 章节。测试 `test_report.py` 断言：报告含 "Android"/"iOS" 两表、总行数覆盖 143、含"不可自动化"与"GitHub Actions"章节标题。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd docs/security/mas-checklist/scripts && python3 -m pytest test_report.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 gen_report.py 使测试通过**

（读 CSV → 统计 → 生成两张分平台表 → 追加 §4/§5 → 写 `MAS-Checklist-Static-Classification.md`）

- [ ] **Step 4: 运行测试确认通过**

Run: `cd docs/security/mas-checklist/scripts && python3 -m pytest test_report.py -v`
Expected: PASS

- [ ] **Step 5: 出 HTML + 发布 Artifact**

用与既有安全文档一致的设计令牌写 `report.html`（总览统计卡 + Android/iOS 分类表 + 不可自动项 + CI 蓝图），调用 Artifact 工具发布。

- [ ] **Step 6: 暂存**

```bash
git add docs/security/mas-checklist/
# 用户确认后 commit
```

---

## 交付物一览（完成后）

```
docs/security/mas-checklist/
├── scripts/          # extract / enrich / annotate / gen_report + 各自 test
├── data/             # mas-static-tests.csv, mas-static-classified.csv
├── sections/         # 04-non-automatable.md, 05-ci-feasibility.md
├── github-actions-blueprint.yml
├── MAS-Checklist-Static-Classification.md   # 汇总报告
└── report.html                              # Artifact 源
```
