# T3 标注上下文（供 subagent 参考）

## MASTG 官方 Android semgrep 规则清单（rules/，命中即 ready_rule=yes）
- mastg-android-asymmetric-key-pair-used-for-multiple-purposes.yml
- mastg-android-backup-manifest.yml
- mastg-android-biometric-device-credential-fallback.yml
- mastg-android-biometric-event-bound.yml
- mastg-android-biometric-invalidated-enrollment.yml
- mastg-android-biometric-no-confirmation-required.yml
- mastg-android-biometric-validity-duration.yml
- mastg-android-broken-encryption-algorithms.yaml
- mastg-android-broken-encryption-modes.yaml
- mastg-android-content-provider-exported.yml
- mastg-android-custom-deeplink-scheme.yml
- mastg-android-dangerous-app-permissions.yaml
- mastg-android-data-unencrypted-shared-storage-no-user-interaction-apis.yml
- mastg-android-data-unencrypted-shared-storage-no-user-interaction-manifest.yml
- mastg-android-debuggable-flag.yml
- mastg-android-debugger-checks.yml
- mastg-android-deeplink-autoverify-missing.yml
- mastg-android-deeplink-unvalidated-parameter.yml
- mastg-android-device-passcode-present.yml
- mastg-android-fileprovider-broad-scope.yml
- mastg-android-hardcoded-crypto-keys-usage.yml
- mastg-android-hardcoded-security-provider.yaml
- mastg-android-implicit-intent-internal-communication.yml
- mastg-android-implicit-intent-leaking-extras.yml
- mastg-android-input-field-usage.yml
- mastg-android-key-generation-with-insufficient-key-length.yml
- mastg-android-keyboard-cache-input-types.yml
- mastg-android-local-storage-input-validation.yml
- mastg-android-native-debugger-checks.yml
- mastg-android-network-checkservertrusted.yml
- mastg-android-network-hostname-verification.yml
- mastg-android-network-insecure-trust-anchors.yml
- mastg-android-network-onreceivedsslerror.yml
- mastg-android-non-random-use.yml
- mastg-android-object-deserialization.yml
- mastg-android-overlay-protection.yml
- mastg-android-pendingintent-mutable.yml
- mastg-android-random-apis-insufficient-entropy.yml
- mastg-android-root-detection.yaml
- mastg-android-sdk-version.yml
- mastg-android-sensitive-data-in-notifications-manifest.yml
- mastg-android-sensitive-data-in-notifications.yml
- mastg-android-sensitive-data-in-screenshot.yml
- mastg-android-sql-injection-contentprovider.yml
- mastg-android-ssl-socket-hostnameverifier.yml
- mastg-android-strictmode.yml
- mastg-android-system-alert-window.yml
- mastg-android-webview-allow-local-access.yml
- mastg-android-webview-bridges.yml
- mastg-android-webview-safebrowsing.yml
- mastg-android-webview-url-handlers.yml

## mobsfscan 覆盖（P0 实测命中过的规则，Android）
- 加密: cbc_padding_oracle, android_kotlin_hardcoded, hardcoded_api_key/password/username
- 平台: android_task_hijacking1/2, webview_javascript_interface, android_hidden_ui
- 存储: android_manifest_missing_explicit_allow_backup, android_prevent_screenshot
- 网络/抗性: android_ssl_pinning, android_root_detection, android_certificate_transparency, android_safetynet
- 日志: android_logging, android_kotlin_logging

## mobsfscan 覆盖（iOS）
- ios_biometric_acl, ios_hardcoded_secret, ios_app_logging/ios_log, ios_load_html_string
- 项目级: ios_cert_pinning, ios_jailbreak_detect, ios_keyboard_cache, ios_detect_reversing 等

## 范围（重要）
**只调研原生代码（Swift / Objective-C / Java / Kotlin）。Dart 业务代码完全不在范围内。**
核心代码=原生代码，只扫这部分。MASTG 的 android/ios test 本就针对原生层，直接对应。**任何判定都不要引入 Dart、不要出现 "Dart" 字样、不要用 needs_custom_rule 表示 Dart 缺口。**

## 判定规则（原生代码）
判定 `ready_rule`（yes / partial / no）+ `gap_note`：
- **yes** = 有现成规则直接覆盖：Android 主题能对应上面 MASTG rules/ 某条规则名，或 mobsfscan 已覆盖该主题。
- **partial** = 有工具但覆盖粗/不精确：
  - iOS **Objective-C** 主题 → 最多 partial（semgrep 不支持 ObjC，只能 mobsfscan libsast 正则，无 AST）。
  - 只有通用 SAST 能初筛、需人工确认的。
- **no** = 无任何现成规则覆盖该原生检查 → gap_note 写"需自写原生 semgrep 规则（Java/Kotlin/Swift）"，替代方案是补原生规则。
补充：
- 从 `title` + `masvs` + `platform` 判断主题即可，不必逐个读 MASTG test 原文。
- iOS Swift 有 mobsfscan + 社区规则 → 视主题判 yes/partial。
- RESILIENCE 的静态项（反调试/完整性/混淆/root-越狱检测）→ 原生层有 mobsfscan 对应项则 yes/partial，纯定制的判 no。
- `ci_feasible` 一律保持 `yes`（原生静态都有 CLI 工具可跑，含 libsast、含待补的自写原生规则）。不要用 needs_custom_rule。
