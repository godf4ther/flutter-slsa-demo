# Flutter SLSA CD Demo —— 设计文档

> 日期：2026-06-25
> 状态：已通过 brainstorming 评审，待用户审阅 → 转实施计划
> 目标读者：本项目维护者 + 后续执行实施计划的 agent

---

## 1. 背景与目标

DeGate 是一个 Flutter 双平台（iOS + Android）项目，当前**没有任何 CI/CD**：发布完全靠本地手动跑 `dart buildScript/scripts/build_script.dart`，iOS 上传用 Apple ID + app-specific password，没有 match、没有产物溯源（provenance）。

我们希望引入 [`qianxiaofeng/fastlane-slsa`](https://github.com/qianxiaofeng/fastlane-slsa) 那套 **GitHub Actions + fastlane + match + SLSA attestation** 流程，让构建产物带上**可验证的 SLSA v1 Build Level 3 provenance**。

`fastlane-slsa` 原项目是**纯 iOS 单平台** PoC，没有覆盖 Android、也没有覆盖 Flutter。直接在 DeGate 生产仓库上改造风险大，因此**本次先在一个独立的 Flutter demo 项目上验证整条流程**。

### 本次目标（终点）

验证一个 Flutter 项目能够通过 fastlane-slsa 流程，**成功 build 出 iOS + Android 产物，并真正上传到 App Store + Google Play**，且产物带可验证的 SLSA L3 provenance。

### 本次范围边界

**只交付 demo**。把独立 demo 项目的双平台 fastlane-slsa CD 跑通并验证。**迁移回 DeGate 主仓库是后续单独任务**，不在本次范围。

---

## 2. 已确认的设计参数

| 维度 | 决策 |
|------|------|
| 平台 | iOS + Android 双平台 |
| Flutter 版本 | 固定 `3.38.10`（与 DeGate 一致），fvm 锁定 |
| demo 位置 | `~/Desktop/flutter-slsa-demo`（degate-app 同级，独立仓库） |
| 终点 | 端到端真发布（build → 上传 App Store + Google Play） |
| 溯源 | 走 fastlane-slsa 流程，产物带 SLSA L3 provenance + SBOM |
| app 记录 | 新建独立 demo（全新 bundle id / package，与 DeGate 生产隔离） |
| iOS 上传凭证 | Apple ID + app-specific password（账号非 Admin，无法建 ASC API Key） |
| Android 上传凭证 | Google Play service account JSON |
| iOS 签名材料 | fastlane match + 独立私有 git 证书仓库 |
| Android 签名材料 | upload keystore，base64 存 GitHub secret，CI 解码 |
| Workflow 编排 | 方案 A：两个独立 reusable workflow（iOS / Android），caller 各调一次 |
| iOS 上传目的地 | App Store Connect / TestFlight（**只上传 binary，不自动提审上架**） |
| Android 上传目的地 | **Internal app sharing**（不进任何测试轨道，不发生产） |
| 交付边界 | 只交付 demo，迁移 DeGate 后续再说 |

### 占位符约定（实施时由用户替换为真实值）

- `<owner>`：demo 代码仓库的 GitHub owner
- `flutter-slsa-demo`：demo 代码仓库名（可改）
- `flutter-slsa-demo-certs`：iOS match 私有证书仓库名（可改）
- `io.slsa.flutterdemo`：iOS bundle id / Android applicationId 示例（可改，两端可一致）

---

## 3. 整体架构

### 3.1 demo 项目目录结构

fastlane 配置放在 `android/fastlane/` 和 `ios/fastlane/` **两个子目录**——这是 Flutter + fastlane 的官方标准约定（fastlane 以"原生平台工程"为工作单位，Flutter 的 `android/`、`ios/` 是两个独立原生子工程）。不同于 fastlane-slsa 的根目录单 `fastlane/`。

```
flutter-slsa-demo/
├── lib/main.dart                    # 最小 Flutter app（一个 SLSA 标识页，重点在 CD 不在业务）
├── pubspec.yaml                     # name: flutter_slsa_demo
│
├── ios/
│   ├── Runner.xcodeproj
│   ├── ExportOptions.plist          # app-store 导出配置
│   └── fastlane/
│       ├── Appfile                  # app_identifier（走 ENV）
│       ├── Matchfile                # match：iOS 证书存独立私有 git 仓库
│       ├── Gemfile                  # fastlane 依赖（iOS）
│       └── Fastfile                 # iOS: build / upload lanes
│
├── android/
│   ├── app/build.gradle             # applicationId、signingConfigs
│   ├── key.properties               # 本地签名配置（gitignore；CI 用 secret 解码生成）
│   └── fastlane/
│       ├── Appfile                  # package_name + json_key（走 ENV）
│       ├── Gemfile                  # fastlane 依赖（Android）
│       └── Fastfile                 # Android: build / upload lanes
│
├── .github/workflows/
│   ├── release.yml                  # caller：何时发布（push v* tag / 手动）
│   ├── build-ios.yml                # reusable（runs-on: macos-26）
│   └── build-android.yml            # reusable（runs-on: ubuntu-latest）
│
├── scripts/bootstrap-local.sh       # 本地一次性：match 创建 iOS 证书 + 生成 Android keystore
├── .gitignore
└── docs/                            # 架构 / 凭证说明（沿用 fastlane-slsa 文档风格，可选）
```

### 3.2 Workflow 分层（方案 A）

```
git push origin v1.0.0
   │
   ▼
release.yml  (caller，决定"何时发布")
   permissions: contents:read · id-token:write · attestations:write
   │
   ├─ job: ios     ──uses──▶ build-ios.yml      (macos-26)    secrets: inherit
   │                          flutter build ipa → match签名 → attest .ipa → 上传 App Store
   │
   └─ job: android ──uses──▶ build-android.yml  (ubuntu-latest) secrets: inherit
                              flutter build aab → keystore签名 → attest .aab → 上传 Internal app sharing
```

两个 job **并行**：iOS 在 macOS、Android 在 ubuntu，各自对自己的产物 attest、各自上传，互不牵连。

**为什么 reusable workflow 是 L3 关键**：GitHub 签发 Sigstore OIDC token 时，token 身份含 `job_workflow_ref`，于是 provenance 的 `builder.id` 绑定到 reusable workflow 的精确引用，调用方仓库无法伪造。caller 必须把 `id-token: write` / `attestations: write` 权限显式下放给 reusable，否则 startup 失败。

---

## 4. iOS 链路（build-ios.yml，runs-on: macos-26）

### 4.1 构建产物契约

`flutter build ipa` 是一等公民，由它产出签名 `.ipa`，fastlane 只负责上传。三个动作锁定**同一个文件** `build/ios/ipa/flutter_slsa_demo.ipa`：

```
flutter build ipa ──▶ build/ios/ipa/flutter_slsa_demo.ipa
                              ├─ attest（SLSA provenance）
                              ├─ SBOM attest（依赖清单）
                              └─ upload（到 App Store Connect）
```

**核心约定**（来自 fastlane-slsa）：attest 的 `subject-path` 必须 == 真正上传的那个文件，否则证明的不是分发的产物。

### 4.2 步骤流

1. checkout
2. 选 Xcode 版本（App Store 上传要求当年 SDK）
3. setup Ruby + bundler（读 `ios/Gemfile`）
4. setup Flutter（pin 版本，可复现）
5. `flutter pub get` + `pod install`
6. 签发证书仓库短期 token（GitHub App，约 1h，只读那一个证书仓库）
7. match (readonly) 装 Apple Distribution 证书 + App Store profile（不登录 Developer Portal、无需 Apple 认证）
8. `update_code_signing_settings` 把 team / 证书 / profile 写进工程（解决 archive 阶段签名）
9. `flutter build ipa` → `build/ios/ipa/*.ipa`（被证明 & 被分发的产物）
10. `attest-build-provenance`（subject-path = 该 .ipa）—— SLSA L3 关键
11. Syft 生成 SBOM + `actions/attest`（绑定同一 .ipa digest）
12. fastlane upload（Apple ID + app-specific password 上传 binary）—— 仅当 `inputs.upload-to-store=true`
13. `upload-artifact` 归档 .ipa + SBOM

### 4.3 签名（match）

- 本地 `bootstrap-local.sh` 用**可写 match** 创建一次证书，加密推到私有证书仓库 `flutter-slsa-demo-certs`。
- CI 用 **readonly match** 只下载解密，不碰 Developer Portal。
- 本地可写 match 用 **Apple ID 登录 Developer Portal + 交互式 2FA** 创建证书；CI 的 readonly match 不登录、无需 Apple 认证（这正是 app-specific password 不能管证书却不影响 CI 的原因）。
- CI clone 证书仓库用 **GitHub App 短期 token**（GitHub Actions OIDC 不能直接 clone 私有 repo，这点 fastlane-slsa 文档讲过）。
- ⚠️ Flutter 坑：`flutter build ipa` 的 archive 阶段需要工程 signing 指向 match 的 profile，用 `update_code_signing_settings` 写入（与 fastlane-slsa 同样处理）。

### 4.4 上传（Apple ID + app-specific password）

- fastlane `upload_to_testflight(username: ENV["FASTLANE_USER"])`，靠 `FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD` env 绕过 2FA。app-specific password 在 appleid.apple.com 自助生成，**不需要 Admin 权限**。
- ⚠️ 局限（fastlane-slsa 文档第 5 节）：app-specific password 只能上传 binary，**不能设 changelog / 管证书**（会触发 Spaceship 登录失败），故 CI 仅上传 + match 走 readonly。
- **语义边界**：上传 = 把 binary 推到 App Store Connect（TestFlight 轨道可见、可供提交），**不自动提交审核上架**。提审是单独的人工决策，CI 不碰。

---

## 5. Android 链路（build-android.yml，runs-on: ubuntu-latest）

### 5.1 构建产物契约（对称于 iOS）

```
flutter build appbundle ──▶ build/app/outputs/bundle/release/app-release.aab
                                    ├─ attest（SLSA provenance）
                                    ├─ SBOM attest（依赖清单）
                                    └─ upload（到 Internal app sharing）
```

Android 在 **ubuntu runner** 上构建（便宜、快），`attest-build-provenance` 跨平台可用，**SLSA L3 同样成立**（reusable workflow + GitHub OIDC + ubuntu 一次性环境）。

### 5.2 步骤流

1. checkout
2. setup Java（JDK 17，Gradle 要求）
3. setup Flutter（pin 版本）
4. setup Ruby + bundler（读 `android/Gemfile`）
5. `flutter pub get`
6. 还原签名材料：base64 secret → 解码出 `upload-keystore.jks`；从 secrets（密码）+ variable（alias）生成 `android/key.properties`
7. `flutter build appbundle` → `app-release.aab`（被证明 & 被分发的产物）
8. `attest-build-provenance`（subject-path = 该 .aab）—— SLSA L3 关键
9. Syft 生成 SBOM + `actions/attest`（绑定同一 .aab digest）
10. fastlane `upload_to_play_store_internal_app_sharing`（service account JSON）—— 仅当 `inputs.upload-to-store=true`
11. `upload-artifact` 归档 .aab + SBOM

### 5.3 签名（keystore）

- 本地 `keytool` 生成 upload keystore 一次（`bootstrap-local.sh`），`base64` 后填进 GitHub secret `ANDROID_KEYSTORE_BASE64`。
- CI 解码还原 keystore 文件，生成 `key.properties`：storePassword / keyPassword 来自 secrets，alias 来自 variable `ANDROID_KEY_ALIAS`。
- Google Play App Signing：用 upload key 签 `.aab`，Google Play 收到后用它自己的 app signing key 重签分发（首次在 Play Console enroll）。

### 5.4 上传（Internal app sharing）

- fastlane `upload_to_play_store_internal_app_sharing`，`json_key_data: ENV[...]`（service account JSON 内容走 secret，不落文件）。
- **语义边界**：上传 = 把 `.aab` 推到 Google Play「内部应用共享」→ 得到分享链接，Play Console「内部应用共享」页可见。**不进任何测试轨道、不走审核、不发生产、不需要 release notes / 测试人员**。
- 额外收益：Internal app sharing 走独立 API，**很可能免掉「首次必须手动上传」** 的限制（它不创建 track release）。

### 5.5 iOS / Android 链路差异对照

| 维度 | iOS（build-ios.yml） | Android（build-android.yml） |
|------|---------------------|------------------------------|
| runner | macos-26（要 Xcode） | ubuntu-latest（便宜并行） |
| 签名机制 | match + 私有 git 证书仓库 | upload keystore（base64 存 secret，CI 解码） |
| 上传凭证 | Apple ID + app-specific password | Google Play service account JSON |
| 上传 lane | `upload_to_testflight(username:)` | `upload_to_play_store_internal_app_sharing` |
| 上传目的地 | TestFlight（不提审） | Internal app sharing（不进轨道） |
| attest 对象 | `build/ios/ipa/*.ipa` | `build/app/outputs/bundle/release/*.aab` |

---

## 6. 凭证清单 + 本地 bootstrap

### 6.1 GitHub Secrets / Variables

**iOS — Secrets（敏感）**

| 名称 | 说明 |
|------|------|
| `MATCH_PASSWORD` | match 加解密口令 |
| `CERT_REPO_APP_PRIVATE_KEY` | GitHub App 私钥（clone 证书仓库用） |
| `CERT_REPO_APP_CLIENT_ID` | GitHub App Client ID |
| `FASTLANE_USER` | Apple ID 邮箱 |
| `FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD` | app-specific password（绕过 2FA 上传） |

**iOS — Variables（非敏感）**：`APP_IDENTIFIER`、`FASTLANE_TEAM_ID`、`MATCH_GIT_URL`、`CERT_REPO_NAME`、`FASTLANE_ITC_TEAM_ID`（可选，多团队时）、`FASTLANE_APP_ID`（可选，ASC 数字 app ID）

**Android — Secrets（敏感）**

| 名称 | 说明 |
|------|------|
| `ANDROID_KEYSTORE_BASE64` | upload keystore 的 base64 |
| `ANDROID_KEYSTORE_PASSWORD` | storePassword |
| `ANDROID_KEY_PASSWORD` | keyPassword |
| `PLAY_SERVICE_ACCOUNT_JSON` | Google Play service account JSON 全文 |

**Android — Variables（非敏感）**：`ANDROID_PACKAGE_NAME`、`ANDROID_KEY_ALIAS`

### 6.2 本地一次性 `bootstrap-local.sh`

- **iOS**：可写 match 创建 Apple Distribution 证书 + App Store profile（登录 Developer Portal + 交互 2FA），加密推到私有证书仓库。
- **Android**：`keytool` 生成 upload keystore 一次 → 提示把 `base64` 结果填进 GitHub secret。

---

## 7. SLSA attest + 验证

### 7.1 双产物对称 attest

两个产物在各自的 reusable workflow 里 attest，`builder.id` 各自绑定到对应 workflow：

```
build-ios.yml      → attest .ipa  → builder.id = .../build-ios.yml@<ref>
build-android.yml  → attest .aab  → builder.id = .../build-android.yml@<ref>
```

每个产物各带 **provenance + SBOM** 两份 attestation。Flutter 的 SBOM 比 fastlane-slsa 更有料：Syft 会扫到 `pubspec.lock`（Dart 依赖）、`Podfile.lock`（iOS）、Gradle 依赖（Android）、`Gemfile.lock`（fastlane 工具链）。

### 7.2 验证命令

```bash
# iOS
gh attestation verify flutter_slsa_demo.ipa \
  --repo <owner>/flutter-slsa-demo \
  --signer-workflow <owner>/flutter-slsa-demo/.github/workflows/build-ios.yml

# Android
gh attestation verify app-release.aab \
  --repo <owner>/flutter-slsa-demo \
  --signer-workflow <owner>/flutter-slsa-demo/.github/workflows/build-android.yml
```

SBOM attestation 按 `--predicate-type https://spdx.dev/Document` 过滤单独验证。

---

## 8. 验收标准（Definition of Done）

1. push 一个 `v*` tag → `release.yml` 触发，**ios / android 两个 job 并行成功**。
2. **iOS**：`.ipa` 构建 → attest → 上传 App Store Connect（TestFlight 可见）。
3. **Android**：`.aab` 构建 → attest → 上传 Internal app sharing（Play Console「内部应用共享」可见 + 分享链接）。
4. 本地 `gh attestation verify` 对两个产物**都通过**（含 `--signer-workflow` 断言）。
5. SBOM attestation 也能按 `--predicate-type` 验证通过。

---

## 9. 已知风险 / 边界

- **外部账号准备耗时**：Google Play 开发者账号需 $25 且可能审核。这是 demo 起步的最大现实门槛（非代码问题）。app-specific password 任何账号自助生成、无门槛。
- **待实施验证的点**：
  - Internal app sharing 是否要求先建 app 记录（保守假设：要建记录，但免手动传 release）。
  - `flutter build ipa` 的 archive 阶段签名（用 `update_code_signing_settings` 兜底，同 fastlane-slsa）。
- **SLSA 信任边界**同 fastlane-slsa：不防平台被攻陷、不防有权限的内鬼。SLSA 转移并收敛信任，不消除信任。
- **第三方 action 全部 pin 到 commit SHA**（与 fastlane-slsa 一致，讲供应链安全的项目尤应如此）。

---

## 10. 不在本次范围（YAGNI）

- 迁移回 DeGate 主仓库（含适配 `buildScript`、多渠道 google_play/samsung/official、混淆、Crashlytics 符号上传）——后续单独任务。
- iOS 真正提交 App Store 审核上架。
- Android 进 internal / closed / production 测试轨道与正式发布。
- demo app 的业务功能（保持最小）。

---

## 11. 前置任务 Checklist（全部由用户人工完成）

> 代码侧（demo app、fastlane 配置、3 个 workflow、bootstrap 脚本）全部按"以下前置已就绪"来写。
> 路径优先级：**5–9（Google Play）是关键路径，建议最先启动**；1–4（Apple）和 10–13（GitHub）相对快。

**Apple 侧**
- [ ] 1. 确认 Apple 账号能登录 Developer Portal 创建证书（Developer / App Manager 角色即可，**不需要 Admin**）
- [ ] 2. 选定 demo 的 iOS bundle id（示例 `io.slsa.flutterdemo`，可改）
- [ ] 3. App Store Connect 建 demo app 记录
- [ ] 4. 在 appleid.apple.com 生成 **app-specific password**（不需要 Admin）；记下 Apple ID 邮箱

**Google 侧**
- [ ] 5. 注册 Google Play 开发者账号（$25，可能要审核）
- [ ] 6. 选定 demo 的 Android applicationId（示例 `io.slsa.flutterdemo`）
- [ ] 7. Play Console 建 demo app 记录（基本信息即可，无需完整商店资料）
- [ ] 8. Play Console 启用 Internal app sharing，并授权 service account
- [ ] 9. GCP 建 service account + Play Console 授予权限 + 下载 JSON

**GitHub 侧**
- [ ] 10. 新建 demo 代码仓库 `flutter-slsa-demo`
- [ ] 11. 新建私有证书仓库 `flutter-slsa-demo-certs`（空仓库即可）
- [ ] 12. 建 GitHub App（只读证书仓库）→ 生成私钥 → 安装到证书仓库
- [ ] 13. 在 demo 仓库配置全部 Secrets + Variables（见第 6 节）

**本机**
- [ ] 14. 装好 Flutter SDK、Xcode、Ruby/bundler、JDK(keytool)
- [ ] 15. 跑 `bootstrap-local.sh`：创建 iOS 证书推证书仓库 + 生成 Android keystore（产出 base64 填进 secret `ANDROID_KEYSTORE_BASE64`）
