# MAS Checklist 静态检查自动化分类报告


> 范围：MASTG v2 静态 test × 原生代码（Swift/ObjC/Java/Kotlin）。Dart 不在范围。数据源 `data/mas-static-classified.csv`。


## 总览

MASTG v2 共 201 个 test，其中**静态 test 143 个**（Android 79 / iOS 64），覆盖全部 8 个 MASVS 组。**只针对原生代码（Swift/ObjC/Java/Kotlin），Dart 业务代码不在范围。**

| 平台 | ✅ 现成规则 | 🟡 部分 | 🔴 需自建 | 小计 |
|---|---|---|---|---|
| android | 51 | 20 | 8 | 79 |
| ios | 14 | 42 | 8 | 64 |
| **合计** | **65** | **62** | **16** | **143** |

档位：可自动（纯静态）**86**，半自动（含 manual、工具初筛+人工确认）**57**。

**一句话结论**：静态原生检查里，65/143 已有现成规则可直接进 CI，62 有工具但需人工确认（iOS ObjC 占多数，因 semgrep 不支持 ObjC 只能 libsast 正则），16 属二进制/SCA 类、需专用工具而非 semgrep。


## 不可自动化 / 需专用工具的静态项（🔴 no）+ 替代方案

### 二进制编译加固标志（PIC / Stack Canary）
`MASTG-TEST-0222`(android)、`MASTG-TEST-0223`(android)、`MASTG-TEST-0228`(ios)、`MASTG-TEST-0229`(ios)

**替代方案**：语义扫描无法判定编译产物属性。替代：`checksec` / `radare2` 对成品二进制静态核验，接进 CI 的构建后步骤。

### 依赖漏洞 / 追踪域名（SCA 类）
`MASTG-TEST-0272`(android)、`MASTG-TEST-0274`(android)、`MASTG-TEST-0273`(ios)、`MASTG-TEST-0275`(ios)、`MASTG-TEST-0281`(ios)

**替代方案**：属软件成分分析，非代码模式。替代：`osv-scanner` / GitHub Dependabot（原生依赖）+ 追踪域名黑名单比对脚本。

### 二进制签名 / 符号表 / 混淆度
`MASTG-TEST-0224`(android)、`MASTG-TEST-0225`(android)、`MASTG-TEST-0288`(android)、`MASTG-TEST-0369`(android)、`MASTG-TEST-0219`(ios)、`MASTG-TEST-0220`(ios)、`MASTG-TEST-0391`(ios)

**替代方案**：同属编译产物属性。替代：`radare2` / `otool` / `nm` 脚本检查符号剥离与签名，构建后跑。

> 这些项虽不能用 semgrep 补规则，但对应工具都是 **CLI、可进 CI**，只是属于二进制/SCA 轨道而非源码 SAST 轨道。


## GitHub Actions 可行性小结

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


## ANDROID 分类明细（79 条，按 checklist 控制项分组）


### ☑️ MASVS-AUTH-2 — The app performs local authentication securely according to the platform best practices.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0326 | auto | ✅ 现成规则 | References to APIs Allowing Fallback to No… |
| MASTG-TEST-0327 | auto | ✅ 现成规则 | References to APIs for Event-Bound Biometr… |
| MASTG-TEST-0328 | auto | ✅ 现成规则 | References to APIs Detecting Biometric Enr… |
| MASTG-TEST-0329 | auto | ✅ 现成规则 | References to APIs Enforcing Authenticatio… |
| MASTG-TEST-0330 | auto | ✅ 现成规则 | References to APIs for Keys used in Biomet… |

### ☑️ MASVS-CODE-1 — The app requires an up-to-date platform version.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0245 | auto | ✅ 现成规则 | References to Platform Version APIs |

### ☑️ MASVS-CODE-2 — The app has a mechanism for enforcing app updates.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0392 | semi | 🟡 部分/需人工确认 | References to Enforced Updating APIs |

### ☑️ MASVS-CODE-3 — The app only uses software components without known vulnerabilities.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0272 | auto | 🔴 需自建/专用工具 | Identify Dependencies with Known Vulnerabi… |
| MASTG-TEST-0274 | auto | 🔴 需自建/专用工具 | Dependencies with Known Vulnerabilities in… |

### ☑️ MASVS-CODE-3; MASVS-CODE-4 — The app only uses software components without known vulnerabilities. / The app validates a
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0222 | auto | 🔴 需自建/专用工具 | Position Independent Code (PIC) Not Enable… |
| MASTG-TEST-0223 | auto | 🔴 需自建/专用工具 | Stack Canaries Not Enabled |

### ☑️ MASVS-CODE-4 — The app validates and sanitizes all untrusted inputs.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0337 | auto | ✅ 现成规则 | References to Object Deserialization of Un… |
| MASTG-TEST-0339 | auto | ✅ 现成规则 | SQL Injection in Content Providers |
| MASTG-TEST-0398 | semi | ✅ 现成规则 | References to WebViewClient URL Loading Ha… |
| MASTG-TEST-0399 | auto | ✅ 现成规则 | SafeBrowsing Disabled |

### ☑️ MASVS-PLATFORM-1; MASVS-STORAGE-2 — The app uses IPC mechanisms securely. / The app prevents leakage of sensitive data.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0372 | semi | ✅ 现成规则 | Implicit Intents Used for Internal App Com… |
| MASTG-TEST-0374 | semi | ✅ 现成规则 | References to Implicit Intents Carrying Se… |

### ☑️ MASVS-CRYPTO-1 — The app employs current strong cryptography and uses it according to industry best practic
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0204 | semi | ✅ 现成规则 | Insecure Random API Usage |
| MASTG-TEST-0205 | semi | ✅ 现成规则 | Non-random Sources Usage |
| MASTG-TEST-0221 | semi | ✅ 现成规则 | Broken Symmetric Encryption Algorithms |
| MASTG-TEST-0232 | semi | ✅ 现成规则 | Broken Symmetric Encryption Modes |
| MASTG-TEST-0309 | auto | 🟡 部分/需人工确认 | References to Reused Initialization Vector… |
| MASTG-TEST-0312 | auto | ✅ 现成规则 | References to Explicit Security Provider i… |

### ☑️ MASVS-CRYPTO-2 — The app performs key management according to industry best practices.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0208 | auto | ✅ 现成规则 | Insufficient Key Sizes |
| MASTG-TEST-0212 | auto | ✅ 现成规则 | Use of Hardcoded Cryptographic Keys in Cod… |
| MASTG-TEST-0307 | auto | ✅ 现成规则 | References to Asymmetric Key Pairs Used Fo… |

### ☑️ MASVS-NETWORK-1 — The app secures all network traffic according to the current best practices.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0217 | auto | 🟡 部分/需人工确认 | Insecure TLS Protocols Explicitly Allowed … |
| MASTG-TEST-0233 | auto | 🟡 部分/需人工确认 | Hardcoded HTTP URLs |
| MASTG-TEST-0234 | auto | ✅ 现成规则 | Missing Implementation of Server Hostname … |
| MASTG-TEST-0235 | auto | 🟡 部分/需人工确认 | Android App Configurations Allowing Cleart… |
| MASTG-TEST-0237 | auto | 🟡 部分/需人工确认 | Cross-Platform Framework Configurations Al… |
| MASTG-TEST-0239 | auto | 🟡 部分/需人工确认 | Using low-level APIs (e.g. Socket) to set … |
| MASTG-TEST-0282 | semi | ✅ 现成规则 | Unsafe Custom Trust Evaluation |
| MASTG-TEST-0283 | semi | ✅ 现成规则 | Incorrect Implementation of Server Hostnam… |
| MASTG-TEST-0284 | semi | ✅ 现成规则 | Incorrect SSL Error Handling in WebViews |
| MASTG-TEST-0285 | auto | 🟡 部分/需人工确认 | Outdated Android Version Allowing Trust in… |
| MASTG-TEST-0286 | auto | ✅ 现成规则 | Network Security Configuration Allowing Tr… |
| MASTG-TEST-0295 | auto | 🟡 部分/需人工确认 | GMS Security Provider Not Updated |

### ☑️ MASVS-NETWORK-2 — The app performs identity pinning for all remote endpoints under the developer's control.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0242 | auto | ✅ 现成规则 | Missing Certificate Pinning in Network Sec… |
| MASTG-TEST-0243 | auto | ✅ 现成规则 | Expired Certificate Pins in the Network Se… |

### ☑️ MASVS-PLATFORM-1 — The app uses IPC mechanisms securely.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0355 | semi | ✅ 现成规则 | References to Unauthorized Database Access… |
| MASTG-TEST-0357 | semi | ✅ 现成规则 | References to Oversharing of File-Based Co… |
| MASTG-TEST-0364 | semi | 🟡 部分/需人工确认 | Exported And Unprotected Activities That E… |
| MASTG-TEST-0365 | semi | 🟡 部分/需人工确认 | Exported And Unprotected Services That Exp… |
| MASTG-TEST-0366 | semi | 🟡 部分/需人工确认 | Exported And Unprotected Broadcast Receive… |
| MASTG-TEST-0381 | auto | ✅ 现成规则 | References to Insecure PendingIntent Creat… |
| MASTG-TEST-0393 | auto | ✅ 现成规则 | Use of Unverified App Links |
| MASTG-TEST-0394 | semi | ✅ 现成规则 | Missing Input Validation in Custom URL Sch… |

### ☑️ MASVS-PLATFORM-2 — The app uses WebViews securely.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0250 | auto | 🟡 部分/需人工确认 | References to Content Provider Access in W… |
| MASTG-TEST-0252 | auto | ✅ 现成规则 | References to Local File Access in WebView… |
| MASTG-TEST-0334 | semi | ✅ 现成规则 | Native Code Exposed Through WebViews |

### ☑️ MASVS-PLATFORM-3 — The app uses the user interface securely.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0258 | auto | ✅ 现成规则 | References to Keyboard Caching Attributes … |
| MASTG-TEST-0291 | auto | ✅ 现成规则 | References to Screen Capturing Prevention … |
| MASTG-TEST-0292 | auto | ✅ 现成规则 | "`setRecentsScreenshotEnabled` Not Used to… |
| MASTG-TEST-0293 | auto | ✅ 现成规则 | "`setSecure` Not Used to Prevent Screensho… |
| MASTG-TEST-0294 | auto | ✅ 现成规则 | "`SecureOn` Not Used to Prevent Screenshot… |
| MASTG-TEST-0315 | auto | ✅ 现成规则 | Sensitive Data Exposed via Notifications |
| MASTG-TEST-0316 | semi | ✅ 现成规则 | App Exposing User Authentication Data in T… |
| MASTG-TEST-0340 | auto | ✅ 现成规则 | References to Overlay Attack Protections |

### ☑️ MASVS-PRIVACY-1 — The app minimizes access to sensitive data and resources.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0254 | auto | ✅ 现成规则 | Dangerous App Permissions |

### ☑️ MASVS-PRIVACY-3 — The app is transparent about data collection and usage.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0318 | auto | 🟡 部分/需人工确认 | References to SDK APIs Known to Handle Sen… |

### ☑️ MASVS-RESILIENCE-1 — The app validates the integrity of the platform.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0247 | auto | ✅ 现成规则 | References to APIs for Detecting Secure Sc… |
| MASTG-TEST-0324 | auto | ✅ 现成规则 | References to Root Detection Mechanisms |

### ☑️ MASVS-RESILIENCE-2 — The app implements anti-tampering mechanisms.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0224 | auto | 🔴 需自建/专用工具 | Usage of Insecure APK Signature Version |
| MASTG-TEST-0225 | auto | 🔴 需自建/专用工具 | Usage of Insecure APK Signature Key Size |
| MASTG-TEST-0338 | semi | ✅ 现成规则 | References to Storage Integrity Check APIs |

### ☑️ MASVS-RESILIENCE-3 — The app implements anti-static analysis mechanisms.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0265 | auto | ✅ 现成规则 | References to StrictMode APIs |
| MASTG-TEST-0288 | auto | 🔴 需自建/专用工具 | Debugging Symbols in Native Binaries |
| MASTG-TEST-0368 | semi | 🟡 部分/需人工确认 | Insufficient Obfuscation of Security-Relev… |
| MASTG-TEST-0369 | semi | 🔴 需自建/专用工具 | Insufficient Obfuscation of Security-Relev… |

### ☑️ MASVS-RESILIENCE-4 — The app implements anti-dynamic analysis techniques.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0226 | auto | ✅ 现成规则 | Debuggable Flag Enabled in the AndroidMani… |
| MASTG-TEST-0227 | auto | 🟡 部分/需人工确认 | Debugging Enabled for WebViews |
| MASTG-TEST-0352 | semi | ✅ 现成规则 | References to Debugging Detection APIs |

### ☑️ MASVS-STORAGE-1 — The app securely stores sensitive data.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0202 | semi | 🟡 部分/需人工确认 | References to APIs and Permissions for Acc… |
| MASTG-TEST-0304 | auto | 🟡 部分/需人工确认 | References to Sensitive Data Unencrypted v… |
| MASTG-TEST-0305 | auto | 🟡 部分/需人工确认 | Sensitive Data Stored Unencrypted via Data… |
| MASTG-TEST-0306 | auto | 🟡 部分/需人工确认 | References to Sensitive Data Stored Unencr… |

### ☑️ MASVS-STORAGE-2 — The app prevents leakage of sensitive data.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0231 | auto | ✅ 现成规则 | References to Logging APIs |
| MASTG-TEST-0262 | auto | ✅ 现成规则 | References to Backup Configurations Not Ex… |

## IOS 分类明细（64 条，按 checklist 控制项分组）


### ☑️ MASVS-AUTH-2 — The app performs local authentication securely according to the platform best practices.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0266 | auto | ✅ 现成规则 | References to APIs for Event-Bound Biometr… |
| MASTG-TEST-0268 | auto | ✅ 现成规则 | References to APIs Allowing Fallback to No… |
| MASTG-TEST-0270 | auto | ✅ 现成规则 | References to APIs Detecting Biometric Enr… |

### ☑️ MASVS-CODE-2 — The app has a mechanism for enforcing app updates.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0383 | semi | 🟡 部分/需人工确认 | References to Enforced Updating APIs |

### ☑️ MASVS-CODE-3 — The app only uses software components without known vulnerabilities.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0273 | auto | 🔴 需自建/专用工具 | Identify Dependencies with Known Vulnerabi… |
| MASTG-TEST-0275 | auto | 🔴 需自建/专用工具 | Dependencies with Known Vulnerabilities in… |

### ☑️ MASVS-CODE-3; MASVS-CODE-4 — The app only uses software components without known vulnerabilities. / The app validates a
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0228 | auto | 🔴 需自建/专用工具 | Position Independent Code (PIC) not Enable… |
| MASTG-TEST-0229 | auto | 🔴 需自建/专用工具 | Stack Canaries Not enabled |
| MASTG-TEST-0230 | auto | 🟡 部分/需人工确认 | Automatic Reference Counting (ARC) not ena… |

### ☑️ MASVS-CODE-4 — The app validates and sanitizes all untrusted inputs.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0386 | semi | 🟡 部分/需人工确认 | References to Object Deserialization of Un… |

### ☑️ MASVS-CRYPTO-1 — The app employs current strong cryptography and uses it according to industry best practic
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0210 | semi | 🟡 部分/需人工确认 | Broken Symmetric Encryption Algorithms |
| MASTG-TEST-0211 | semi | 🟡 部分/需人工确认 | Broken Hashing Algorithms |
| MASTG-TEST-0311 | semi | 🟡 部分/需人工确认 | Insecure Random API Usage |
| MASTG-TEST-0317 | semi | 🟡 部分/需人工确认 | Broken Symmetric Encryption Modes |

### ☑️ MASVS-CRYPTO-2 — The app performs key management according to industry best practices.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0209 | auto | 🟡 部分/需人工确认 | Insufficient Key Sizes |
| MASTG-TEST-0213 | semi | ✅ 现成规则 | Use of Hardcoded Cryptographic Keys in Cod… |
| MASTG-TEST-0214 | semi | ✅ 现成规则 | Hardcoded Cryptographic Keys in Files |

### ☑️ MASVS-NETWORK-1 — The app secures all network traffic according to the current best practices.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0321 | auto | 🟡 部分/需人工确认 | Hardcoded HTTP URLs |
| MASTG-TEST-0322 | semi | 🟡 部分/需人工确认 | App Transport Security Configurations Allo… |
| MASTG-TEST-0323 | semi | 🟡 部分/需人工确认 | Uses of Low-Level Networking APIs for Clea… |
| MASTG-TEST-0342 | auto | 🟡 部分/需人工确认 | References to Weak ATS TLS Policy Exceptio… |
| MASTG-TEST-0343 | semi | 🟡 部分/需人工确认 | URLSession TLS Protocol Configuration |
| MASTG-TEST-0344 | semi | 🟡 部分/需人工确认 | Network.framework TLS Protocol Configurati… |
| MASTG-TEST-0345 | semi | 🟡 部分/需人工确认 | Embedded or Third-party TLS Stack Configur… |
| MASTG-TEST-0396 | semi | ✅ 现成规则 | References to URLSessionDelegate Bypassing… |
| MASTG-TEST-0397 | semi | ✅ 现成规则 | References to WKNavigationDelegate Bypassi… |

### ☑️ MASVS-NETWORK-2 — The app performs identity pinning for all remote endpoints under the developer's control.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0385 | auto | ✅ 现成规则 | Missing Certificate Pinning in ATS |

### ☑️ MASVS-PLATFORM-1 — The app uses IPC mechanisms securely.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0370 | auto | 🟡 部分/需人工确认 | Missing Input Validation in Custom URL Sch… |
| MASTG-TEST-0371 | auto | 🟡 部分/需人工确认 | Missing Source Validation in Custom URL Sc… |
| MASTG-TEST-0389 | semi | 🟡 部分/需人工确认 | References to the App-Wide Restriction of … |
| MASTG-TEST-0390 | semi | 🟡 部分/需人工确认 | Full Access Requested by a Custom Keyboard… |
| MASTG-TEST-0395 | semi | 🟡 部分/需人工确认 | Missing Input Validation in Universal Link… |

### ☑️ MASVS-PLATFORM-2 — The app uses WebViews securely.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0331 | auto | 🟡 部分/需人工确认 | Use of Deprecated WebView APIs |
| MASTG-TEST-0332 | semi | ✅ 现成规则 | Attacker-Controlled URI in WebViews |
| MASTG-TEST-0333 | semi | 🟡 部分/需人工确认 | Overly Broad File Read Access in WebViews |
| MASTG-TEST-0335 | semi | 🟡 部分/需人工确认 | WebView File Origin Access Relaxed by Conf… |
| MASTG-TEST-0376 | auto | 🟡 部分/需人工确认 | References to Native Bridge APIs in WebVie… |
| MASTG-TEST-0377 | semi | 🟡 部分/需人工确认 | References to `evaluateJavaScript` Used as… |
| MASTG-TEST-0378 | semi | 🟡 部分/需人工确认 | References to Password Fields in WebView-L… |
| MASTG-TEST-0379 | auto | 🟡 部分/需人工确认 | References to `evaluateJavaScript` Without… |
| MASTG-TEST-0380 | semi | 🟡 部分/需人工确认 | References to `evaluateJavaScript` Writing… |

### ☑️ MASVS-PLATFORM-3 — The app uses the user interface securely.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0276 | semi | 🟡 部分/需人工确认 | Use of the iOS General Pasteboard |
| MASTG-TEST-0278 | auto | 🟡 部分/需人工确认 | Pasteboard Contents Not Cleared After Use |
| MASTG-TEST-0279 | auto | 🟡 部分/需人工确认 | Pasteboard Contents Not Expiring |
| MASTG-TEST-0280 | auto | 🟡 部分/需人工确认 | Pasteboard Contents Not Restricted to Loca… |
| MASTG-TEST-0346 | semi | 🟡 部分/需人工确认 | References to APIs Hiding Sensitive Data i… |

### ☑️ MASVS-PRIVACY-1 — The app minimizes access to sensitive data and resources.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0281 | auto | 🔴 需自建/专用工具 | Undeclared Known Tracking Domains |
| MASTG-TEST-0360 | semi | 🟡 部分/需人工确认 | Purpose String Accuracy for Reachable Prot… |
| MASTG-TEST-0362 | semi | 🟡 部分/需人工确认 | Entitlements for Unjustified Capability Ex… |

### ☑️ MASVS-RESILIENCE-1 — The app validates the integrity of the platform.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0240 | auto | ✅ 现成规则 | Jailbreak Detection in Code |
| MASTG-TEST-0248 | auto | 🟡 部分/需人工确认 | References to APIs for Detecting Secure Sc… |

### ☑️ MASVS-RESILIENCE-2 — The app implements anti-tampering mechanisms.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0220 | auto | 🔴 需自建/专用工具 | Usage of Outdated Code Signature Format |
| MASTG-TEST-0387 | semi | 🟡 部分/需人工确认 | References to Storage Integrity Check APIs |

### ☑️ MASVS-RESILIENCE-3 — The app implements anti-static analysis mechanisms.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0219 | auto | 🔴 需自建/专用工具 | Testing for Debugging Symbols |
| MASTG-TEST-0358 | auto | ✅ 现成规则 | Implementation Details Exposure Through Lo… |
| MASTG-TEST-0391 | semi | 🔴 需自建/专用工具 | Insufficient Obfuscation of Security-Relev… |

### ☑️ MASVS-RESILIENCE-4 — The app implements anti-dynamic analysis techniques.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0261 | auto | 🟡 部分/需人工确认 | Debuggable Entitlement Enabled in the enti… |
| MASTG-TEST-0401 | semi | ✅ 现成规则 | References to Debugging Detection APIs |

### ☑️ MASVS-STORAGE-1 — The app securely stores sensitive data.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0300 | auto | 🟡 部分/需人工确认 | References to APIs for Storing Unencrypted… |
| MASTG-TEST-0303 | auto | 🟡 部分/需人工确认 | References to APIs for Storing Unencrypted… |
| MASTG-TEST-0388 | semi | 🟡 部分/需人工确认 | References to Sensitive Data Stored Unprot… |

### ☑️ MASVS-STORAGE-2 — The app prevents leakage of sensitive data.
| TEST | 档位 | 现成规则 | 说明 |
|---|---|---|---|
| MASTG-TEST-0215 | auto | 🟡 部分/需人工确认 | Sensitive Data Not Marked For Backup Exclu… |
| MASTG-TEST-0297 | auto | ✅ 现成规则 | Sensitive Data Exposure Through Logging AP… |
| MASTG-TEST-0313 | semi | ✅ 现成规则 | References to APIs for Preventing Keyboard… |