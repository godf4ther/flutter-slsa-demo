# Flutter SLSA CD Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零搭建一个独立 Flutter demo 项目，通过 fastlane-slsa 流程在 GitHub Actions 上构建 iOS + Android 产物、生成可验证的 SLSA L3 provenance，并上传到 App Store Connect（TestFlight）与 Google Play（Internal app sharing）。

**Architecture:** caller workflow（`release.yml`）+ 两个独立 reusable workflow（`build-ios.yml` 跑 macOS、`build-android.yml` 跑 ubuntu，方案 A）。每个平台各自 `flutter build` → 签名 → `attest-build-provenance` → 上传。iOS 签名走 fastlane match + 私有 git 证书仓库、上传走 Apple ID + app-specific password；Android 签名走 base64 keystore + key.properties，上传走 Google Play service account JSON。

**Tech Stack:** Flutter / Dart、fastlane（match / gym / pilot / supply）、GitHub Actions、Sigstore（`actions/attest-build-provenance`）、Syft（SBOM）。

**对应设计文档：** [`docs/superpowers/specs/2026-06-25-flutter-slsa-cd-demo-design.md`](../specs/2026-06-25-flutter-slsa-cd-demo-design.md)

## Global Constraints

- **demo 项目位置**：建在桌面 `~/Desktop/flutter-slsa-demo`（= `degate-app` 同级，独立 git 仓库，与 DeGate 完全隔离）。
- **Flutter 版本**：固定 `3.38.10`（与 DeGate 一致，已装于 `~/fvm/versions/3.38.10`）。本地用 fvm 锁定（项目 `.fvmrc`），本地 flutter/dart 命令走 `fvm` 前缀；CI 用 `subosito/flutter-action` 的 `flutter-version: 3.38.10`（不用 `channel: stable`）。
- **bundle id / package**：`io.slsa.flutterdemo`（iOS 与 Android 一致；若用户前置任务选了别的值，全局替换）。
- **pubspec name**：`flutter_slsa_demo`。
- **所有第三方 GitHub Action 必须 pin 到 commit SHA**（`#` 后注版本号），不用可变 tag。
- **所有账号/凭证走环境变量**（CI 用 secrets/variables 注入），绝不写死进仓库。
- **iOS 必须 macos-26 runner**（App Store 上传要求当年 iOS SDK / Xcode 26）；Android 用 ubuntu-latest。
- **构建产物固定路径（契约）**：iOS = `build/ios/ipa/flutter_slsa_demo.ipa`；Android = `build/app/outputs/bundle/release/app-release.aab`。`attest` 的 `subject-path` 必须等于真正上传的这个文件。
- **CI 的 match 永远 readonly**（`is_ci` 控制）；证书的创建只在本地 `bootstrap-local.sh`（可写 match）发生一次。
- **上传语义**：iOS 只上传 binary 到 App Store Connect（TestFlight 可见），**不提审上架**；Android 走 Internal app sharing，**不进任何测试轨道**。
- **前置凭证由用户人工完成**（见设计文档第 11 节 Checklist）。Phase 0–4 的代码/配置编写**不依赖**真实凭证；Phase 5 的真发布验收**依赖**凭证就绪。

## 验证策略（本计划如何"测试"）

| 层 | 验证手段 |
|----|---------|
| demo app（Dart） | `flutter test`（widget test，走 TDD） + `flutter analyze` |
| fastlane 配置（Ruby DSL） | `bundle exec fastlane <platform> lanes`（能列出 lane = 语法正确） |
| workflow（YAML） | `actionlint`（若装）或 `python -c 'import yaml,sys;yaml.safe_load(...)'` 语法校验 + GitHub Actions 解析 |
| bash 脚本 | `bash -n`（语法）+ `shellcheck`（若装） |
| 构建可行性 | 本地 `flutter build ios --no-codesign` / `flutter build appbundle`（临时 keystore） |
| 端到端（Phase 5） | push `v*` tag → CI 两 job 成功 → `gh attestation verify` 通过 |

---

## File Structure

```
../flutter-slsa-demo/
├── lib/main.dart                          # Task 0.1 最小 SLSA 标识页
├── test/widget_test.dart                  # Task 0.1 widget test
├── pubspec.yaml                           # flutter create 生成，Task 0.1 调整 name
├── .gitignore                             # Task 0.1 + Task 2.1 补充签名材料忽略
│
├── ios/
│   ├── Runner.xcodeproj / Runner.xcworkspace
│   └── fastlane/
│       ├── Appfile                        # Task 1.1
│       ├── Matchfile                      # Task 1.1
│       ├── Gemfile                        # Task 1.1
│       └── Fastfile                       # Task 1.2
│
├── android/
│   ├── app/build.gradle(.kts)             # Task 2.1 signingConfigs
│   ├── key.properties                     # Task 2.1 模板（gitignore；CI 生成）
│   └── fastlane/
│       ├── Appfile                        # Task 2.2
│       ├── Gemfile                        # Task 2.2
│       └── Fastfile                       # Task 2.2
│
├── .github/workflows/
│   ├── build-ios.yml                      # Task 3.1（macos-26）
│   ├── build-android.yml                  # Task 3.2（ubuntu）
│   └── release.yml                        # Task 3.3（caller）
│
└── scripts/bootstrap-local.sh             # Task 4.1
```

---

## Phase 0：项目脚手架与最小 app

### Task 0.1：创建 demo 项目 + 最小 SLSA 标识页（TDD）

**Files:**
- Create: `../flutter-slsa-demo/`（`flutter create` 生成）
- Modify: `../flutter-slsa-demo/lib/main.dart`
- Create: `../flutter-slsa-demo/test/widget_test.dart`
- Modify: `../flutter-slsa-demo/pubspec.yaml`（name）

**Interfaces:**
- Produces: `SlsaDemoApp`（`StatelessWidget`，无参构造 `const SlsaDemoApp({super.key})`）——后续无代码依赖，仅供 widget test 与构建。

- [ ] **Step 1: 创建项目（用 Flutter 3.38.10）**

```bash
cd ~/Desktop
fvm spawn 3.38.10 create --org io.slsa --project-name flutter_slsa_demo --platforms ios,android flutter-slsa-demo
cd flutter-slsa-demo
fvm use 3.38.10 --force   # 写入 .fvmrc 锁定版本，与 DeGate 一致
```

> 说明：用 `fvm spawn 3.38.10` 精确用 DeGate 同款版本创建（已装于 `~/fvm/versions/3.38.10`）；`fvm use` 写入项目 `.fvmrc`，之后本项目命令都走 `fvm flutter`/`fvm dart`。`--org io.slsa` + `--project-name flutter_slsa_demo` 让 bundle id / applicationId 默认 `io.slsa.flutterSlsaDemo`；下一步统一改成约定的 `io.slsa.flutterdemo`。

- [ ] **Step 2: 统一 bundle id / applicationId 为 `io.slsa.flutterdemo`**

```bash
# iOS：改 project.pbxproj 里的 PRODUCT_BUNDLE_IDENTIFIER（3 处，含 RunnerTests 用 .RunnerTests）
/usr/bin/sed -i '' 's/io\.slsa\.flutterSlsaDemo/io.slsa.flutterdemo/g' ios/Runner.xcodeproj/project.pbxproj
# Android：改 applicationId / namespace
grep -rl 'io.slsa.flutterSlsaDemo' android/app/ | xargs /usr/bin/sed -i '' 's/io\.slsa\.flutterSlsaDemo/io.slsa.flutterdemo/g'
```

验证：`grep -r 'io.slsa.flutterdemo' ios/Runner.xcodeproj/project.pbxproj android/app/` 应能看到改后的值。

- [ ] **Step 3: 写失败的 widget test**

`test/widget_test.dart`（覆盖 `flutter create` 生成的默认 counter 测试）：

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_slsa_demo/main.dart';

void main() {
  testWidgets('渲染 SLSA 标识页', (tester) async {
    await tester.pumpWidget(const SlsaDemoApp());
    expect(find.text('Flutter + fastlane + SLSA'), findsOneWidget);
    expect(find.byIcon(Icons.verified), findsOneWidget);
  });
}
```

- [ ] **Step 4: 运行测试确认失败**

Run: `fvm flutter test`
Expected: FAIL —— `SlsaDemoApp` 未定义（main.dart 还是默认模板）。

- [ ] **Step 5: 实现最小 app**

`lib/main.dart`（整文件替换）：

```dart
import 'package:flutter/material.dart';

void main() => runApp(const SlsaDemoApp());

class SlsaDemoApp extends StatelessWidget {
  const SlsaDemoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter SLSA Demo',
      home: Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: const [
              Icon(Icons.verified, size: 96, color: Colors.green),
              SizedBox(height: 16),
              Text(
                'Flutter + fastlane + SLSA',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text(
                '这个产物由 GitHub Actions 构建，\n并附带 SLSA Build L3 provenance。',
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 6: 运行测试与分析确认通过**

Run: `fvm flutter test && fvm flutter analyze`
Expected: 测试 PASS；analyze 无 error。

- [ ] **Step 7: 提交**

```bash
git add -A
git commit -m "chore: scaffold flutter-slsa-demo with minimal SLSA identity page"
```

---

## Phase 1：iOS fastlane 与签名配置

### Task 1.1：iOS fastlane 基础配置（Appfile / Matchfile / Gemfile）

**Files:**
- Create: `ios/fastlane/Appfile`
- Create: `ios/fastlane/Matchfile`
- Create: `ios/fastlane/Gemfile`

**Interfaces:**
- Produces: 环境变量契约 `APP_IDENTIFIER`、`FASTLANE_USER`、`FASTLANE_TEAM_ID`、`FASTLANE_ITC_TEAM_ID`、`FASTLANE_APP_ID`、`MATCH_GIT_URL`、`MATCH_READONLY`、`MATCH_PASSWORD`、`FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD`——Task 1.2 的 Fastfile 与 Task 3.1 的 workflow 都依赖这些名字。

- [ ] **Step 1: 创建 `ios/fastlane/Appfile`**

```ruby
# 应用与账号基本信息，全部从环境变量读取（不写死进仓库）。
app_identifier(ENV["APP_IDENTIFIER"] || "io.slsa.flutterdemo")
# Apple ID（开发者账号邮箱）。CI 由 secret FASTLANE_USER 注入；本地可写 match 与上传都用它。
apple_id(ENV["FASTLANE_USER"])
team_id(ENV["FASTLANE_TEAM_ID"])
# App Store Connect 团队 ID（账号属多团队时需要）。
itc_team_id(ENV["FASTLANE_ITC_TEAM_ID"]) if ENV["FASTLANE_ITC_TEAM_ID"]
```

- [ ] **Step 2: 创建 `ios/fastlane/Matchfile`**

```ruby
# match：加密的签名证书 + provisioning profile 存放在一个独立私有 git 仓库。
git_url(ENV["MATCH_GIT_URL"])
storage_mode("git")
type("appstore")
app_identifier([ENV["APP_IDENTIFIER"] || "io.slsa.flutterdemo"])
# CI 强制 readonly（Fastfile 用 is_ci 控制；这里给保险默认）。
readonly(ENV["MATCH_READONLY"] == "true")
```

- [ ] **Step 3: 创建 `ios/fastlane/Gemfile`**

```ruby
source "https://rubygems.org"
gem "fastlane"
```

- [ ] **Step 4: 校验 + 安装依赖**

Run:
```bash
cd ios && bundle install && bundle exec fastlane ios lanes; cd ..
```
Expected: `bundle install` 成功；`fastlane ios lanes` 此时 lane 为空但**不报语法错误**（Fastfile 尚未建，会提示无 lane，正常）。

- [ ] **Step 5: 提交**

```bash
git add ios/fastlane/Appfile ios/fastlane/Matchfile ios/fastlane/Gemfile ios/Gemfile.lock
git commit -m "feat(ios): add fastlane Appfile/Matchfile/Gemfile"
```

### Task 1.2：iOS Fastfile（setup_signing / build / upload lanes）

**Files:**
- Create: `ios/fastlane/Fastfile`

**Interfaces:**
- Consumes: Task 1.1 的环境变量契约。
- Produces: lane `ios setup_signing`、`ios build`（产出 `build/ios/ipa/flutter_slsa_demo.ipa`）、`ios upload`——Task 3.1 的 workflow 调用这些 lane。

- [ ] **Step 1: 创建 `ios/fastlane/Fastfile`**

```ruby
# 职责：fastlane 负责【签名打包 .ipa】与【上传】。SLSA provenance 由 GitHub workflow 生成。
default_platform(:ios)

# 产物固定路径契约：仓库根 build/ios/ipa/flutter_slsa_demo.ipa（workflow 据此 attest）。
OUTPUT_DIR  = File.expand_path("../../build/ios/ipa", __dir__)
OUTPUT_NAME = "flutter_slsa_demo.ipa"

platform :ios do
  desc "下载签名证书与 profile（CI 中 readonly，不登录 Developer Portal）"
  lane :setup_signing do
    setup_ci if is_ci
    # CI：readonly 只 clone + 解密证书，不碰 Apple 账号；本地可写时用 Appfile 的 apple_id 登录 + 交互 2FA。
    match(type: "appstore", readonly: is_ci)
  end

  desc "构建签名 .ipa（gym 接管 archive + 签名 + export）"
  lane :build do
    setup_signing
    app_id = ENV.fetch("APP_IDENTIFIER")

    # Flutter 工程默认 manual 签名但未绑定 profile/team；把 match 装好的证书/profile
    # 写进工程，解决 archive 阶段 "requires a provisioning profile"。
    update_code_signing_settings(
      use_automatic_signing: false,
      path: "Runner.xcodeproj",
      team_id: ENV.fetch("FASTLANE_TEAM_ID"),
      bundle_identifier: app_id,
      code_sign_identity: "Apple Distribution",
      profile_name: "match AppStore #{app_id}",
    )

    # gym archive 一个 Flutter iOS workspace 时，xcodebuild 会触发工程内的
    # flutter assemble build phase 完成 Dart 编译；export_options 由 gym 动态生成，
    # 因此无需维护静态 ExportOptions.plist。
    build_app(
      workspace: "Runner.xcworkspace",
      scheme: "Runner",
      export_method: "app-store",
      output_directory: OUTPUT_DIR,
      output_name: OUTPUT_NAME,
      clean: true,
      xcargs: "CURRENT_PROJECT_VERSION=#{ENV['GITHUB_RUN_NUMBER'] || '1'}",
      export_options: {
        signingStyle: "manual",
        provisioningProfiles: { app_id => "match AppStore #{app_id}" },
      },
    )
    UI.success("已生成签名 .ipa: #{File.join(OUTPUT_DIR, OUTPUT_NAME)}")
  end

  desc "上传 .ipa 到 TestFlight（Apple ID + app-specific password，绕过 2FA，不提审上架）"
  lane :upload do
    # FASTLANE_USER + FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD 由 env 提供，
    # upload_to_testflight 底层 altool 据此绕过 2FA。app-specific password 只能上传 binary，
    # 不能设 changelog / 管证书（会触发 Spaceship 登录失败），故 CI 仅上传。
    upload_to_testflight(
      username: ENV.fetch("FASTLANE_USER"),
      apple_id: ENV["FASTLANE_APP_ID"], # ASC 里 app 的数字 ID（可选，加速定位）
      ipa: File.join(OUTPUT_DIR, OUTPUT_NAME),
      skip_waiting_for_build_processing: true,
    )
    UI.success("已上传 TestFlight: #{OUTPUT_NAME}")
  end
end
```

- [ ] **Step 2: 校验 lane 语法**

Run: `cd ios && bundle exec fastlane ios lanes; cd ..`
Expected: 列出 `setup_signing`、`build`、`upload` 三个 lane，无语法错误。

- [ ] **Step 3: 提交**

```bash
git add ios/fastlane/Fastfile
git commit -m "feat(ios): add fastlane build/upload lanes (match + gym + app-specific password)"
```

---

## Phase 2：Android fastlane 与签名配置

### Task 2.1：Android release 签名配置（signingConfigs + key.properties + gitignore）

**Files:**
- Modify: `android/app/build.gradle` 或 `android/app/build.gradle.kts`
- Create: `android/key.properties`（本地模板；CI 生成同名文件）
- Modify: `.gitignore`

**Interfaces:**
- Produces: `key.properties` 字段契约 `storeFile` / `storePassword` / `keyAlias` / `keyPassword`——Task 4.1 的 bootstrap 与 Task 3.2 的 workflow 据此生成。

- [ ] **Step 1: 确认 Gradle DSL 类型**

Run: `ls android/app/build.gradle android/app/build.gradle.kts 2>/dev/null`
Expected: 只存在其一。较新 Flutter 是 `.kts`（Kotlin DSL），较老是 `.gradle`（Groovy）。下一步按存在的那个选模板。

- [ ] **Step 2a（若是 Groovy `build.gradle`）：加签名配置**

在 `android {` 块**之前**加载 key.properties：

```groovy
def keystoreProperties = new Properties()
def keystorePropertiesFile = rootProject.file('key.properties')
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}
```

在 `android { ... }` 内加 signingConfigs，并把 release 指向它：

```groovy
android {
    signingConfigs {
        release {
            if (keystorePropertiesFile.exists()) {
                storeFile file(keystoreProperties['storeFile'])
                storePassword keystoreProperties['storePassword']
                keyAlias keystoreProperties['keyAlias']
                keyPassword keystoreProperties['keyPassword']
            }
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
        }
    }
}
```

- [ ] **Step 2b（若是 Kotlin `build.gradle.kts`）：加签名配置**

文件顶部 import 后加载：

```kotlin
import java.util.Properties
import java.io.FileInputStream

val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("key.properties")
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
}
```

`android { ... }` 内：

```kotlin
signingConfigs {
    create("release") {
        if (keystorePropertiesFile.exists()) {
            storeFile = file(keystoreProperties["storeFile"] as String)
            storePassword = keystoreProperties["storePassword"] as String
            keyAlias = keystoreProperties["keyAlias"] as String
            keyPassword = keystoreProperties["keyPassword"] as String
        }
    }
}
buildTypes {
    getByName("release") {
        signingConfig = signingConfigs.getByName("release")
    }
}
```

- [ ] **Step 3: 创建本地 `android/key.properties` 模板**

```properties
storeFile=upload-keystore.jks
storePassword=changeit-local-only
keyAlias=upload
keyPassword=changeit-local-only
```

> 注：这是本地占位模板，真实值由 `bootstrap-local.sh`（本地）和 CI（secrets）写入。文件必须 gitignore。

- [ ] **Step 4: 追加 `.gitignore`**

```gitignore
# Android 签名材料（绝不入库）
android/key.properties
**/upload-keystore.jks
*.jks
*.keystore
```

- [ ] **Step 5: 校验 Gradle 配置**

Run: `cd android && ./gradlew tasks -q >/dev/null && echo OK; cd ..`
Expected: 打印 `OK`（Gradle 能解析 build 配置，无语法错误）。

- [ ] **Step 6: 确认 key.properties 未被跟踪**

Run: `git check-ignore android/key.properties`
Expected: 输出 `android/key.properties`（已被忽略）。

- [ ] **Step 7: 提交**

```bash
git add android/app/build.gradle* .gitignore
git commit -m "feat(android): add release signingConfig reading key.properties"
```

### Task 2.2：Android fastlane（Appfile / Gemfile / Fastfile upload lane）

**Files:**
- Create: `android/fastlane/Appfile`
- Create: `android/fastlane/Gemfile`
- Create: `android/fastlane/Fastfile`

**Interfaces:**
- Consumes: 环境变量 `ANDROID_PACKAGE_NAME`、`PLAY_SERVICE_ACCOUNT_JSON`。
- Produces: lane `android upload`（上传 `build/app/outputs/bundle/release/app-release.aab` 到 Internal app sharing）——Task 3.2 的 workflow 调用。

- [ ] **Step 1: 创建 `android/fastlane/Appfile`**

```ruby
package_name(ENV["ANDROID_PACKAGE_NAME"] || "io.slsa.flutterdemo")
# json_key 走 ENV（CI），不写死路径。
```

- [ ] **Step 2: 创建 `android/fastlane/Gemfile`**

```ruby
source "https://rubygems.org"
gem "fastlane"
```

- [ ] **Step 3: 创建 `android/fastlane/Fastfile`**

```ruby
# 职责：Android 由 `flutter build appbundle` 完成签名构建，fastlane 只负责上传。
default_platform(:android)

# 产物固定路径契约（相对仓库根）。
AAB_PATH = File.expand_path("../../build/app/outputs/bundle/release/app-release.aab", __dir__)

platform :android do
  desc "上传 .aab 到 Google Play Internal app sharing（不进测试轨道、不审核）"
  lane :upload do
    upload_to_play_store_internal_app_sharing(
      aab: AAB_PATH,
      package_name: ENV.fetch("ANDROID_PACKAGE_NAME"),
      json_key_data: ENV.fetch("PLAY_SERVICE_ACCOUNT_JSON"),
    )
    UI.success("已上传 Internal app sharing: #{AAB_PATH}")
  end
end
```

- [ ] **Step 4: 校验 lane 语法**

Run: `cd android && bundle install && bundle exec fastlane android lanes; cd ..`
Expected: 列出 `upload` lane，无语法错误。

- [ ] **Step 5: 提交**

```bash
git add android/fastlane/Appfile android/fastlane/Gemfile android/fastlane/Fastfile android/Gemfile.lock
git commit -m "feat(android): add fastlane upload lane (Play internal app sharing)"
```

---

## Phase 3：GitHub Actions workflows

> 本 Phase 的 workflow 文件先用可读 tag 写 Flutter/Java action，Task 3.4 统一 pin 到 SHA。
> fastlane-slsa 已验证的 action SHA 直接采用（见各 `uses:` 注释）。

### Task 3.1：build-ios.yml（reusable，macos-26）

**Files:**
- Create: `.github/workflows/build-ios.yml`

**Interfaces:**
- Consumes: secrets `MATCH_PASSWORD` / `CERT_REPO_APP_PRIVATE_KEY` / `CERT_REPO_APP_CLIENT_ID` / `FASTLANE_USER` / `FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD`；variables `APP_IDENTIFIER` / `FASTLANE_TEAM_ID` / `MATCH_GIT_URL` / `CERT_REPO_NAME` / `FASTLANE_ITC_TEAM_ID` / `FASTLANE_APP_ID`；Task 1.2 的 `ios build` / `ios upload` lane。
- Produces: workflow_call 接口 `inputs.upload-to-store`（boolean）；attestation 绑定到本文件路径。

- [ ] **Step 1: 创建 `.github/workflows/build-ios.yml`**

```yaml
name: Build, Sign & Attest iOS (reusable)

on:
  workflow_call:
    inputs:
      upload-to-store:
        description: "构建并 attest 后是否上传 App Store Connect"
        type: boolean
        default: false

permissions: {}

jobs:
  build-ios:
    runs-on: macos-26
    permissions:
      contents: read
      id-token: write        # Sigstore OIDC
      attestations: write    # 写 artifact attestation
    env:
      APP_IDENTIFIER: ${{ vars.APP_IDENTIFIER }}
      FASTLANE_TEAM_ID: ${{ vars.FASTLANE_TEAM_ID }}
      MATCH_GIT_URL: ${{ vars.MATCH_GIT_URL }}
      MATCH_READONLY: "true"
      MATCH_PASSWORD: ${{ secrets.MATCH_PASSWORD }}
      FASTLANE_ITC_TEAM_ID: ${{ vars.FASTLANE_ITC_TEAM_ID }}
      FASTLANE_APP_ID: ${{ vars.FASTLANE_APP_ID }}
      FASTLANE_USER: ${{ secrets.FASTLANE_USER }}
      FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD: ${{ secrets.FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD }}
    steps:
      - name: Checkout
        uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0

      - name: 选择 Xcode 版本
        run: |
          XCODE=$(ls -d /Applications/Xcode_26*.app 2>/dev/null | sort -V | tail -1)
          [ -z "$XCODE" ] && XCODE=$(ls -d /Applications/Xcode_*.app | sort -V | tail -1)
          echo "使用 $XCODE"
          sudo xcode-select -switch "$XCODE"

      - name: 安装 Flutter
        uses: subosito/flutter-action@v2   # Task 3.4 pin SHA
        with:
          flutter-version: 3.38.10   # 与 DeGate 一致
          cache: true

      - name: 安装 Ruby 与 fastlane 依赖
        uses: ruby/setup-ruby@9eb537ca036ebaed86729dcb9309076e4c5c3b74 # v1.314.0
        with:
          ruby-version: "3.3"
          bundler-cache: true
          working-directory: ios

      - name: flutter pub get + 生成 iOS 配置
        run: |
          flutter pub get
          flutter build ios --release --config-only --no-codesign

      - name: pod install（仅当存在 Podfile；无 CocoaPods 插件的项目自动跳过）
        working-directory: ios
        run: |
          if [ -f Podfile ]; then pod install; else echo "无 Podfile（项目无 CocoaPods 插件），跳过 pod install"; fi

      - name: 签发证书仓库短期访问 token
        id: cert-token
        uses: actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1 # v3.2.0
        with:
          client-id: ${{ secrets.CERT_REPO_APP_CLIENT_ID }}
          private-key: ${{ secrets.CERT_REPO_APP_PRIVATE_KEY }}
          owner: ${{ github.repository_owner }}
          repositories: ${{ vars.CERT_REPO_NAME }}

      - name: 用短期 token 组装 match git 凭证
        run: |
          AUTH=$(printf 'x-access-token:%s' '${{ steps.cert-token.outputs.token }}' | base64 | tr -d '\n')
          echo "::add-mask::$AUTH"
          echo "MATCH_GIT_BASIC_AUTHORIZATION=$AUTH" >> "$GITHUB_ENV"

      - name: 构建签名 .ipa（match + gym）
        working-directory: ios
        run: bundle exec fastlane ios build

      - name: 打印产物 SHA-256
        run: shasum -a 256 build/ios/ipa/flutter_slsa_demo.ipa

      - name: 生成 SLSA Build Provenance
        uses: actions/attest-build-provenance@a2bbfa25375fe432b6a289bc6b6cd05ecd0c4c32 # v4.1.0
        with:
          subject-path: build/ios/ipa/flutter_slsa_demo.ipa

      - name: 生成 SBOM（Syft → SPDX JSON）
        uses: anchore/sbom-action@e22c389904149dbc22b58101806040fa8d37a610 # v0.24.0
        with:
          path: "."
          format: spdx-json
          output-file: build/ios/ipa/flutter_slsa_demo.sbom.spdx.json
          upload-artifact: false

      - name: 为 .ipa 生成 SBOM attestation
        uses: actions/attest@59d89421af93a897026c735860bf21b6eb4f7b26 # v4.1.0
        with:
          subject-path: build/ios/ipa/flutter_slsa_demo.ipa
          sbom-path: build/ios/ipa/flutter_slsa_demo.sbom.spdx.json

      - name: 上传 App Store Connect（可选）
        if: ${{ inputs.upload-to-store }}
        working-directory: ios
        run: bundle exec fastlane ios upload

      - name: 归档产物
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: ios-ipa
          path: |
            build/ios/ipa/flutter_slsa_demo.ipa
            build/ios/ipa/flutter_slsa_demo.sbom.spdx.json
          if-no-files-found: error
```

- [ ] **Step 2: 校验 YAML 语法**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build-ios.yml'))" && echo OK`
Expected: 打印 `OK`。

- [ ] **Step 3: 提交**

```bash
git add .github/workflows/build-ios.yml
git commit -m "feat(ci): add reusable build-ios workflow (build+attest+upload)"
```

### Task 3.2：build-android.yml（reusable，ubuntu）

**Files:**
- Create: `.github/workflows/build-android.yml`

**Interfaces:**
- Consumes: secrets `ANDROID_KEYSTORE_BASE64` / `ANDROID_KEYSTORE_PASSWORD` / `ANDROID_KEY_PASSWORD` / `PLAY_SERVICE_ACCOUNT_JSON`；variables `ANDROID_PACKAGE_NAME` / `ANDROID_KEY_ALIAS`；Task 2.2 的 `android upload` lane。
- Produces: workflow_call 接口 `inputs.upload-to-store`。

- [ ] **Step 1: 创建 `.github/workflows/build-android.yml`**

```yaml
name: Build, Sign & Attest Android (reusable)

on:
  workflow_call:
    inputs:
      upload-to-store:
        description: "构建并 attest 后是否上传 Google Play Internal app sharing"
        type: boolean
        default: false

permissions: {}

jobs:
  build-android:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
      attestations: write
    env:
      ANDROID_PACKAGE_NAME: ${{ vars.ANDROID_PACKAGE_NAME }}
      PLAY_SERVICE_ACCOUNT_JSON: ${{ secrets.PLAY_SERVICE_ACCOUNT_JSON }}
    steps:
      - name: Checkout
        uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0

      - name: 安装 Java
        uses: actions/setup-java@v4   # Task 3.4 pin SHA
        with:
          distribution: temurin
          java-version: "17"

      - name: 安装 Flutter
        uses: subosito/flutter-action@v2   # Task 3.4 pin SHA
        with:
          flutter-version: 3.38.10   # 与 DeGate 一致
          cache: true

      - name: 安装 Ruby 与 fastlane 依赖
        uses: ruby/setup-ruby@9eb537ca036ebaed86729dcb9309076e4c5c3b74 # v1.314.0
        with:
          ruby-version: "3.3"
          bundler-cache: true
          working-directory: android

      - name: 还原签名材料（keystore + key.properties）
        env:
          ANDROID_KEYSTORE_BASE64: ${{ secrets.ANDROID_KEYSTORE_BASE64 }}
          ANDROID_KEYSTORE_PASSWORD: ${{ secrets.ANDROID_KEYSTORE_PASSWORD }}
          ANDROID_KEY_PASSWORD: ${{ secrets.ANDROID_KEY_PASSWORD }}
          ANDROID_KEY_ALIAS: ${{ vars.ANDROID_KEY_ALIAS }}
        run: |
          echo "$ANDROID_KEYSTORE_BASE64" | base64 --decode > android/app/upload-keystore.jks
          cat > android/key.properties <<EOF
          storeFile=upload-keystore.jks
          storePassword=$ANDROID_KEYSTORE_PASSWORD
          keyAlias=$ANDROID_KEY_ALIAS
          keyPassword=$ANDROID_KEY_PASSWORD
          EOF

      - name: flutter pub get
        run: flutter pub get

      - name: 构建签名 .aab
        run: flutter build appbundle --release

      - name: 打印产物 SHA-256
        run: sha256sum build/app/outputs/bundle/release/app-release.aab

      - name: 生成 SLSA Build Provenance
        uses: actions/attest-build-provenance@a2bbfa25375fe432b6a289bc6b6cd05ecd0c4c32 # v4.1.0
        with:
          subject-path: build/app/outputs/bundle/release/app-release.aab

      - name: 生成 SBOM（Syft → SPDX JSON）
        uses: anchore/sbom-action@e22c389904149dbc22b58101806040fa8d37a610 # v0.24.0
        with:
          path: "."
          format: spdx-json
          output-file: build/app/outputs/bundle/release/app-release.sbom.spdx.json
          upload-artifact: false

      - name: 为 .aab 生成 SBOM attestation
        uses: actions/attest@59d89421af93a897026c735860bf21b6eb4f7b26 # v4.1.0
        with:
          subject-path: build/app/outputs/bundle/release/app-release.aab
          sbom-path: build/app/outputs/bundle/release/app-release.sbom.spdx.json

      - name: 上传 Google Play Internal app sharing（可选）
        if: ${{ inputs.upload-to-store }}
        working-directory: android
        run: bundle exec fastlane android upload

      - name: 归档产物
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: android-aab
          path: |
            build/app/outputs/bundle/release/app-release.aab
            build/app/outputs/bundle/release/app-release.sbom.spdx.json
          if-no-files-found: error
```

- [ ] **Step 2: 校验 YAML 语法**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build-android.yml'))" && echo OK`
Expected: 打印 `OK`。

- [ ] **Step 3: 提交**

```bash
git add .github/workflows/build-android.yml
git commit -m "feat(ci): add reusable build-android workflow (build+attest+upload)"
```

### Task 3.3：release.yml（caller）

**Files:**
- Create: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: Task 3.1 / 3.2 的 reusable workflow。

- [ ] **Step 1: 创建 `.github/workflows/release.yml`**

```yaml
name: Release

on:
  push:
    tags:
      - "v*"
  workflow_dispatch:
    inputs:
      upload-to-store:
        description: "构建后是否上传商店"
        type: boolean
        default: false

jobs:
  ios:
    permissions:
      contents: read
      id-token: write
      attestations: write
    uses: ./.github/workflows/build-ios.yml
    with:
      upload-to-store: ${{ github.event_name == 'push' || inputs.upload-to-store }}
    secrets: inherit

  android:
    permissions:
      contents: read
      id-token: write
      attestations: write
    uses: ./.github/workflows/build-android.yml
    with:
      upload-to-store: ${{ github.event_name == 'push' || inputs.upload-to-store }}
    secrets: inherit
```

- [ ] **Step 2: 校验 YAML 语法**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))" && echo OK`
Expected: 打印 `OK`。

- [ ] **Step 3: 提交**

```bash
git add .github/workflows/release.yml
git commit -m "feat(ci): add caller release workflow (ios + android parallel)"
```

### Task 3.4：把 Flutter / Java action pin 到 commit SHA

**Files:**
- Modify: `.github/workflows/build-ios.yml`、`.github/workflows/build-android.yml`

- [ ] **Step 1: 查出 SHA**

```bash
gh api repos/subosito/flutter-action/commits/v2 --jq '.sha'
gh api repos/actions/setup-java/commits/v4 --jq '.sha'
```

- [ ] **Step 2: 替换两处 `subosito/flutter-action@v2` 与一处 `actions/setup-java@v4`**

把 `subosito/flutter-action@v2` 改为 `subosito/flutter-action@<sha> # v2`（两个 workflow 各一处）；把 `actions/setup-java@v4` 改为 `actions/setup-java@<sha> # v4`（build-android.yml 一处），`<sha>` 用 Step 1 查到的值。

- [ ] **Step 3: 校验 + 提交**

Run:
```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build-ios.yml')); yaml.safe_load(open('.github/workflows/build-android.yml'))" && echo OK
```
Expected: `OK`。

```bash
git add .github/workflows/build-ios.yml .github/workflows/build-android.yml
git commit -m "chore(ci): pin flutter-action and setup-java to commit SHA"
```

---

## Phase 4：本地 bootstrap 脚本

### Task 4.1：scripts/bootstrap-local.sh

**Files:**
- Create: `scripts/bootstrap-local.sh`

**Interfaces:**
- Consumes: 环境变量 `APP_IDENTIFIER` / `FASTLANE_USER` / `FASTLANE_TEAM_ID` / `MATCH_GIT_URL` / `MATCH_PASSWORD`。
- Produces: 私有证书仓库里的加密 iOS 证书；本地 `android/app/upload-keystore.jks` + base64 字符串。

- [ ] **Step 1: 创建 `scripts/bootstrap-local.sh`**

```bash
#!/usr/bin/env bash
# 本地一次性引导：
#   1) iOS：可写 match 创建并加密证书/profile，推到私有证书仓库（CI 之后 readonly 复用）。
#   2) Android：keytool 生成 upload keystore，输出 base64 供填入 GitHub secret。
#
# 用法（先 export 一组环境变量）：
#   export APP_IDENTIFIER=io.slsa.flutterdemo
#   export FASTLANE_TEAM_ID=ABCDE12345
#   export MATCH_GIT_URL=https://github.com/<you>/flutter-slsa-demo-certs.git
#   export MATCH_PASSWORD='强口令'
#   export FASTLANE_USER=you@apple.id
#   ./scripts/bootstrap-local.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> 检查必需环境变量"
: "${APP_IDENTIFIER:?需要 APP_IDENTIFIER}"
: "${FASTLANE_TEAM_ID:?需要 FASTLANE_TEAM_ID}"
: "${MATCH_GIT_URL:?需要 MATCH_GIT_URL（私有证书仓库）}"
: "${MATCH_PASSWORD:?需要 MATCH_PASSWORD}"
: "${FASTLANE_USER:?需要 FASTLANE_USER（Apple ID 邮箱）}"

echo "==> [iOS] 首次可写 match（登录 Developer Portal 创建证书，按提示完成 2FA）"
( cd ios && bundle install && MATCH_READONLY=false bundle exec fastlane ios setup_signing )

echo "==> [Android] 生成 upload keystore（若不存在）"
KS=android/app/upload-keystore.jks
if [ ! -f "$KS" ]; then
  keytool -genkey -v -keystore "$KS" -keyalg RSA -keysize 2048 -validity 10000 \
    -alias upload -dname "CN=SLSA Demo, OU=Dev, O=SLSA, L=NA, S=NA, C=NA" \
    -storepass "${ANDROID_KEYSTORE_PASSWORD:-changeit}" -keypass "${ANDROID_KEY_PASSWORD:-changeit}"
else
  echo "    已存在 $KS，跳过生成"
fi

echo "==> [Android] keystore base64（填入 GitHub secret ANDROID_KEYSTORE_BASE64）："
base64 -i "$KS" | tr -d '\n'; echo

echo "==> 完成。证书已推到 ${MATCH_GIT_URL}；keystore 在 ${KS}。"
echo "    下一步：在 demo 仓库配置 secrets/variables（见设计文档第 6 节）后即可触发 CI。"
```

- [ ] **Step 2: 加可执行位 + 语法检查**

Run:
```bash
git add --chmod=+x scripts/bootstrap-local.sh
bash -n scripts/bootstrap-local.sh && echo OK
```
Expected: 打印 `OK`（无语法错误）。

- [ ] **Step 3: 提交**

```bash
git add scripts/bootstrap-local.sh
git commit -m "feat: add local bootstrap script (iOS match + Android keystore)"
```

---

## Phase 5：端到端验收（依赖用户前置凭证就绪）

> 本 Phase 需要设计文档第 11 节的前置任务全部完成（账号、app 记录、key、证书仓库、GitHub App、secrets/variables 已配）。

### Task 5.1：本地免凭证构建冒烟（不需要真实凭证）

- [ ] **Step 1: iOS 免签名构建**

Run: `fvm flutter build ios --release --no-codesign`
Expected: 构建成功，产出 `build/ios/iphoneos/Runner.app`（证明 Flutter iOS 编译链路通）。

- [ ] **Step 2: Android 临时签名构建**

```bash
# 临时本地 keystore（仅冒烟用）
keytool -genkey -v -keystore android/app/upload-keystore.jks -keyalg RSA -keysize 2048 \
  -validity 365 -alias upload -dname "CN=smoke" -storepass changeit -keypass changeit
printf 'storeFile=upload-keystore.jks\nstorePassword=changeit\nkeyAlias=upload\nkeyPassword=changeit\n' > android/key.properties
fvm flutter build appbundle --release
```
Expected: 产出 `build/app/outputs/bundle/release/app-release.aab`。
清理：`rm android/app/upload-keystore.jks android/key.properties`（勿入库）。

### Task 5.2：本地 bootstrap + 配置 secrets（用户操作，依赖前置）

- [ ] **Step 1:** 按设计文档第 11 节完成所有前置任务（Apple / Google / GitHub / 本机）。
- [ ] **Step 2:** export 环境变量后跑 `./scripts/bootstrap-local.sh`，把输出的 base64 填入 secret `ANDROID_KEYSTORE_BASE64`，并配齐设计文档第 6 节的所有 secrets/variables。
- [ ] **Step 3:** push demo 项目到 GitHub `<owner>/flutter-slsa-demo`。

### Task 5.3：触发发布并验证 provenance

- [ ] **Step 1: 触发**

```bash
git tag v0.1.0
git push origin v0.1.0
```
Expected: `release.yml` 触发，`ios` 与 `android` 两个 job 并行成功。

- [ ] **Step 2: 验证两个产物的 attestation**

下载两个 artifact 后：

```bash
gh attestation verify flutter_slsa_demo.ipa \
  --repo <owner>/flutter-slsa-demo \
  --signer-workflow <owner>/flutter-slsa-demo/.github/workflows/build-ios.yml

gh attestation verify app-release.aab \
  --repo <owner>/flutter-slsa-demo \
  --signer-workflow <owner>/flutter-slsa-demo/.github/workflows/build-android.yml
```
Expected: 两条命令均退出码 0（含 `--signer-workflow` 断言通过）。

- [ ] **Step 3: 验证 SBOM attestation**

```bash
gh attestation verify flutter_slsa_demo.ipa \
  --repo <owner>/flutter-slsa-demo \
  --predicate-type https://spdx.dev/Document \
  --signer-workflow <owner>/flutter-slsa-demo/.github/workflows/build-ios.yml
```
Expected: 退出码 0。

- [ ] **Step 4: 确认上传**

- App Store Connect → TestFlight：能看到上传的 build。
- Google Play Console → 内部应用共享：能看到 `.aab` + 分享链接。

**验收完成 = 设计文档第 8 节 Definition of Done 全部满足。**
