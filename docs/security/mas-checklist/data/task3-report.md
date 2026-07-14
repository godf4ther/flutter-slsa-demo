# Task 3：MASTG 静态 test 现成规则覆盖标注报告

范围：仅原生代码（Swift / Objective-C / Java / Kotlin）静态检查，143 条 MASTG 静态 test 全量标注。
判定依据：`_t3-context.md`（MASTG 官方 Android semgrep rules/ 51 条清单 + mobsfscan 实测覆盖列表）。
产出脚本：`scripts/annotate_gaps.py`，写回 `data/mas-static-classified.csv`（新增 `ready_rule`、`gap_note` 两列，`ci_feasible` 统一保持 `yes`）。

## 统计（按平台）

| platform | yes | partial | no | 合计 |
|---|---|---|---|---|
| android | 51 | 20 | 8 | 79 |
| ios | 14 | 42 | 8 | 64 |
| **合计** | **65** | **62** | **16** | **143** |

- `ready_rule=yes`：主题精确对应 MASTG 官方 semgrep rules/ 某条规则名，或 mobsfscan 已实测覆盖该主题，可直接复用。
- `ready_rule=partial`：有工具但覆盖粗/不精确——iOS 侧因 Objective-C 无 semgrep AST 支持只能靠 mobsfscan libsast 正则初筛（iOS 42 条全部属于此类），或只有通用 SAST 能初筛、结论仍需人工确认。
- `ready_rule=no`：无任何现成规则覆盖，需自写原生规则或引入专用工具（详见下表）。

## 需自写原生规则 / 专用工具（ready_rule=no，共 16 条）

这 16 条按缺口类型分三类，均**不是**普通语义 semgrep 模式匹配能补齐的：

### 1. 二进制编译标志检查（4 条）—— 需 readelf/otool/checksec 类工具
- MASTG-TEST-0222　Position Independent Code (PIC) Not Enabled（android）
- MASTG-TEST-0223　Stack Canaries Not Enabled（android）
- MASTG-TEST-0228　Position Independent Code (PIC) not Enabled（ios）
- MASTG-TEST-0229　Stack Canaries Not enabled（ios）

### 2. 二进制签名/符号表/混淆度检查（4 条）—— 需 apksigner/codesign/nm/strip 类工具
- MASTG-TEST-0224　Usage of Insecure APK Signature Version（android）
- MASTG-TEST-0225　Usage of Insecure APK Signature Key Size（android）
- MASTG-TEST-0288　Debugging Symbols in Native Binaries（android）
- MASTG-TEST-0369　Insufficient Obfuscation of Security-Relevant Native Code（android）
- MASTG-TEST-0219　Testing for Debugging Symbols（ios）
- MASTG-TEST-0220　Usage of Outdated Code Signature Format（ios）
- MASTG-TEST-0391　Insufficient Obfuscation of Security-Relevant Native Code（ios）

### 3. 依赖漏洞比对（SCA）/ 追踪域名库比对（3 条）—— 需专用数据库比对工具
- MASTG-TEST-0272　Identify Dependencies with Known Vulnerabilities in the Android Project（android，需 OWASP Dependency-Check / Trivy）
- MASTG-TEST-0274　Dependencies with Known Vulnerabilities in the App's SBOM（android，同上）
- MASTG-TEST-0273　Identify Dependencies with Known Vulnerabilities by Scanning Dependency Managers Artifacts（ios，需 Trivy/Grype）
- MASTG-TEST-0275　Dependencies with Known Vulnerabilities in the App's SBOM（ios，同上）
- MASTG-TEST-0281　Undeclared Known Tracking Domains（ios，需第三方追踪域名库比对工具）

合计：android 8 条（编译标志 2 + 签名/符号/混淆 4 + SCA 2），ios 8 条（编译标志 2 + 签名/符号/混淆 3 + SCA 2 + 追踪域名 1）。

## iOS Objective-C partial 说明（42 条）

iOS 侧除 14 条精确命中 mobsfscan 主题（生物识别 ACL、硬编码密钥、证书锁定/绕过、jailbreak 检测、日志、键盘缓存、反调试/反逆向、WebView URL 加载）外，其余 42 条均标为 `partial`：语言层面若为 Objective-C，semgrep 无 AST 支持只能靠 mobsfscan libsast 正则初筛；若为 Swift 可结合 mobsfscan/社区规则（akabe1/insideapp）进一步初筛，但均无精确命中的官方规则，结论仍需人工确认。这 42 条不计入"无覆盖"（no），因为至少有通用 SAST 可初筛，缺口可通过补充原生 libsast 正则或自写规则弥补精度，而非从零开始。

## 结论

- 65/143（约 45%）可直接复用现成规则（MASTG 官方 semgrep rules 或 mobsfscan 实测项），CI 落地成本最低。
- 62/143（约 43%）有工具可初筛但精度不足，需人工复核或后续补充 libsast/自写规则，其中 42 条集中在 iOS（Objective-C 覆盖天然弱于 Swift）。
- 16/143（约 11%）完全无现成规则覆盖，且不属于常规 semgrep 模式匹配范畴（二进制标志/签名/符号表/混淆度检查需专用二进制分析工具，依赖漏洞与追踪域名比对需专用数据库类工具），是后续 CI 自动化中优先级最高、投入产出比需要单独评估的缺口项。
