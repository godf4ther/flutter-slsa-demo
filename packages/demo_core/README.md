# demo_core — MAS 静态扫描演示插件

> ⚠️ **本插件的原生代码故意埋入了安全漏洞**，仅用于演示"把 MAS Checklist 静态检查继承进 GitHub CI"。**请勿在任何生产代码中参考这些实现。**

模拟一个"自有核心 SDK"（Flutter plugin），核心逻辑放在**原生层**（Swift / Objective-C / Java / Kotlin），业务层 Dart 只是空壳——对应真实项目里"核心代码=原生代码，只扫这部分"的约定。

## 故意埋入的漏洞（→ 对应 MASTG 静态检查项 → 谁扫出）

| 文件 | 语言 | 漏洞 | MASTG | 扫描器 |
|---|---|---|---|---|
| `android/…/DemoCorePlugin.kt` | Kotlin | 硬编码密钥 | TEST-0212 | mobsfscan `android_kotlin_hardcoded` |
| | | `java.util.Random` 做 nonce | TEST-0204/0205 | mobsfscan `android_kotlin_insecure_random` |
| | | AES/CBC + 全零 IV | TEST-0232 | mobsfscan `cbc_kotlin_padding_oracle` |
| `android/…/LegacyCrypto.java` | Java | DES/ECB 弱加密 | TEST-0221/0232 | semgrep `mastg-android-broken-encryption-*` |
| | | 硬编码口令 | TEST-0212 | mobsfscan `hardcoded_password` |
| `ios/Classes/DemoCore.swift` | Swift | 硬编码密钥 | TEST-0213/0214 | mobsfscan `ios_hardcoded_secret` |
| | | MD5 弱哈希 | — | mobsfscan `ios_weak_hash` |
| `ios/Classes/LegacyCrypto.m` | ObjC | 硬编码 secret | — | mobsfscan `ios_hardcoded_secret`(libsast) |

## CI

`.github/workflows/mas-static-scan.yml`：push/PR 触发 → semgrep(MASTG规则+p/java+p/kotlin) + mobsfscan 扫本插件原生代码 → SARIF 上传到 Security → Code scanning。

**结论**：semgrep 与 mobsfscan 组合覆盖全部 4 语言（ObjC 靠 mobsfscan libsast）；单用任一工具都有盲区。
