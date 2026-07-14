# MAS Checklist 静态检查自动化可行性调研 — 设计文档

- **日期**：2026-07-13
- **状态**：设计已通过，待 review → 写实施计划
- **范围**：仅静态代码扫描（动态测试后续单独立项）

## 1. 背景与目标

DeGate 是 Flutter 加密钱包 App。此前已完成 P0 首轮安全扫描（semgrep + mobsfscan + MASTG 官方规则 + 社区规则），验证了工具链在本项目上可用。

本任务把目标从"跑一次扫描"提升为**调研 + 实践**：

1. **拉全** MAS Checklist（<https://mas.owasp.org/checklists/>）里所有 check 项。
2. 按 MASTG 文档判定**哪些能自动化、用什么工具**，**iOS / Android 分开列**。能脚本自动化的即可继承进 CI。
3. **列出不能自动化的项**，调研替代方案。

关键约束：

- 本次**只做静态代码扫描**，动态向（Frida / reFlutter / MobSF 动态）先不考虑。
- **只扫原生代码（Swift / Objective-C / Java / Kotlin）**，Dart 业务代码不在范围。核心代码=原生代码，将来核心/业务代码分离后只扫核心原生。MASTG 的 android/ios test 本就针对原生层，直接对应，不存在"Dart 层"翻译问题。
- **不需要真实运行的 CI 流水线**。最终 CI 会落在 GitHub Actions，本次只调研"继承这些检查脚本进 GitHub CI 的可行性"，产出蓝图而非运维中的流水线。
- 可新建 demo 项目作为演示载体（本设计聚焦分类矩阵；demo/PoC 的具体形态在实施计划阶段决定）。

## 2. 范围（Scope）

### In scope

- MASTG v2 `tests-beta/` 中 **143 个 `type` 含 `static` 的 test**，覆盖全部 8 个 MASVS 组（AUTH / CODE / CRYPTO / NETWORK / PLATFORM / PRIVACY / RESILIENCE / STORAGE）。
  - **Android 79**：纯 static（可自动）55 + static+manual（半自动）24
  - **iOS 64**：纯 static（可自动）31 + static+manual（半自动）33
- 全量分类，保留 `profiles`（L1 / L2 / R / P）标注，便于后续筛选到钱包对标的 L2 + R。

### Out of scope（本次不做）

- 58 个纯动态 test（`dynamic/hooks/network/filesystem/logs`）—— 留待后续「动态测试自动化」专项。
- 实际编写并运行 GitHub Actions 流水线 —— 本次只出 workflow 蓝图。
- 完整补齐 Dart 自定义规则 —— 本次只**标注**哪些需自写，不实现全量规则（PoC 规模的规则示例可选）。

## 3. 数据源与方法论

### 权威数据源

MAS Checklist 本质是 MASVS 控制 → MASTG test 的一个视图。本地已克隆 OWASP/mastg，其 `tests-beta/` 的 201 个 test YAML frontmatter 提供客观、机器可读的字段：

- `platform`（android / ios / network）—— 天然满足"iOS/Android 分开"
- `type`（static / dynamic / code / config / manual / hooks …）—— **自动化可行性的一手信号**
- `profiles`（L1 / L2 / R / P）、`weakness`（MASWE）、MASVS 分类（目录）

### 自动化档位映射（由 `type` 决定，机械规则）

| type 特征 | 档位 | 含义 |
|---|---|---|
| 含 `static`，不含 `manual` | **可自动** | SAST 工具直接取证 |
| 含 `static` 且含 `manual` | **半自动** | 工具出候选，人工确认（仍可进 CI 做初筛） |
| （纯动态） | 排除 | 本次不做 |

### 工具映射（结合 P0 实证）

| 目标代码 | 工具 | 现成规则 |
|---|---|---|
| Android Java/Kotlin | MASTG 52 条 semgrep 规则 + mobsfscan + `p/java`/`p/kotlin` | 有（P0 已验证） |
| iOS Swift | mobsfscan + akabe1 / insideapp 社区规则 | 部分（官方少，社区补） |
| iOS Objective-C | mobsfscan（libsast 正则）| 有限（semgrep 不支持 ObjC） |
| Manifest / plist / config | mobsfscan + MASTG config 规则 | 有 |

> **范围提醒**：Dart（`lib/`）不在本次范围。核心代码=原生代码，只扫原生。无 Dart 自写规则一说。

## 4. 交付物结构

一份分类矩阵文档（markdown + 可分享 Artifact），回答三个问题：

1. **已拉全**：静态 checklist 全集，按 MASVS 控制组织，标 profile。
2. **可自动化矩阵**（Android / iOS 分表）：每行 = `test ID · MASVS · type · 档位 · 工具 · 是否已有现成规则（引用 P0）· 能否进 GitHub CI · 备注`。
3. **不可自动化的静态项 + 替代方案**：
   - Dart 层无现成规则 → 自写
   - iOS ObjC semgrep 不支持 → mobsfscan libsast / 手动
   - 本质是"人工代码审查"的 static+manual 项 → 审查清单化 / attestation

外加：

- **总览**：每平台 可自动 / 半自动 / 不可自动 占比 + 工具覆盖图。
- **GitHub Actions 可行性小结**：静态项容器化（无需 emulator）、workflow 骨架示意、diff-aware 扫描、SARIF 上报、各工具 runner 需求。

## 5. 分类判定规则（Rubric）

为保证 143 条分类**可复现、可审计**，每条 test 走统一判定：

1. 读 frontmatter：`platform` / `type` / `profiles` / MASVS。
2. 档位：由 `type` 是否含 `manual` 决定（可自动 / 半自动）。
3. 工具：由 `platform` + 目标语言层 + §3 工具映射表决定；标注是否已有现成规则（对照 P0 实测或 MASTG `rules/`）。
4. CI 可行性：可自动 / 半自动且存在 CLI 工具 → CI 可行（静态无需 emulator）；仅当**无任何工具可覆盖**（如 Dart 无规则且未自写）时标"待自建"。
5. 替代方案：对"不可自动"或"待自建"给出具体路径（自写规则 / libsast / 手动清单）。

## 6. 成功标准

- 143 个静态 test 全部分类完毕，Android / iOS 分开成表。
- 每个可自动项标注**具体工具** + **是否有现成规则**（引用 P0 实证）。
- 每个不可自动项有**明确替代方案**。
- 产出能直接指导后续实施计划（写 GitHub Actions workflow 蓝图 + 补 Dart 规则清单）。

## 7. 执行方式

- **数据驱动 + 人工富化**：脚本解析 143 个 YAML 拿客观字段（确定性），再逐条做工具映射与 Flutter 现实判断。
- 不引入真实 CI；GitHub Actions 部分只产出蓝图与可行性结论。

## 8. 后续（本次范围外，供上下文）

- 动态测试自动化（Frida / reFlutter / MobSF 动态）单独立项。reFlutter 已验证支持本项目 Flutter 3.38.10。
- 把蓝图落成真实 GitHub Actions workflow + 补齐 Dart 自定义规则。
- 用 MAS Checklist 汇总证据、做 L2+R gap 分析（P1）。
