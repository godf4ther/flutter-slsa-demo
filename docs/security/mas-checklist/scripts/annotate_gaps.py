#!/usr/bin/env python3
"""给 143 个 MASTG 静态 test 标注 ready_rule / gap_note。

范围：只判定原生代码（Swift / Objective-C / Java / Kotlin）静态检查能否被
现成规则（MASTG 官方 semgrep rules/ 或 mobsfscan 内置规则）覆盖。判定依据见
`_t3-context.md`：
  - ready_rule=yes   : 主题精确对应 MASTG rules/ 某条规则名，或 mobsfscan 已覆盖该主题
  - ready_rule=partial: 有工具但覆盖粗/不精确（iOS Objective-C 只能 libsast 正则；
                         或只有通用 SAST 能初筛，需人工确认）
  - ready_rule=no    : 无任何现成规则覆盖，需自写原生规则或引入专用工具
ci_feasible 统一保持 yes（原生静态检查都有 CLI 工具可跑）。
"""
import os
import csv

HERE = os.path.dirname(__file__)
IN = os.path.join(HERE, "..", "data", "mas-static-classified.csv")
OUT = IN  # 写回同一文件

DEFAULT = ("partial", "无精确现成规则，通用 SAST 初筛后人工确认")

# iOS 非 yes/no 项的统一 partial 说明：语言层面 Objective-C 与 Swift 混合，
# semgrep 对 ObjC 无 AST 支持，只能靠 mobsfscan libsast 正则初筛；
# Swift 部分可结合 mobsfscan/社区规则（akabe1/insideapp）初筛，但均无精确命中的官方规则，仍需人工确认。
IOS_OBJC_PARTIAL_NOTE = (
    "iOS 原生若为 Objective-C，semgrep 无 AST 支持，仅能靠 mobsfscan libsast 正则初筛；"
    "若为 Swift 可结合 mobsfscan/社区规则（akabe1/insideapp）进一步初筛，但均无精确命中的官方规则，"
    "仍需人工确认；缺口可通过补充原生 libsast 正则或自写规则弥补精度"
)

# 二进制层检查（编译标志/签名/符号表/混淆）：不是源码模式匹配问题，semgrep/mobsfscan
# 规则天然覆盖不到，需要专门的二进制检测工具或脚本。
BIN_NOTE_ANDROID_PIC_CANARY = (
    "二进制编译标志检查（PIE/Stack Canary），非源码模式匹配范畴，MASTG/mobsfscan 均无覆盖；"
    "需自写脚本用 readelf/checksec 类工具检测 .so 二进制编译标志，非 semgrep 规则可解决"
)
BIN_NOTE_IOS_PIC_CANARY = (
    "二进制层 Mach-O 编译标志检查（PIE/Stack Canary），非源码模式匹配范畴；"
    "需 otool/checksec 类工具检测二进制编译标志，非 semgrep 规则可解决"
)
SCA_NOTE_ANDROID = (
    "依赖已知漏洞比对属于 SCA（软件成分分析），非 semgrep 模式匹配范畴；"
    "需引入专用 SCA 工具（如 OWASP Dependency-Check / Trivy）扫描 Gradle 依赖或 SBOM，而非自写 semgrep 规则"
)
SCA_NOTE_IOS = (
    "依赖已知漏洞比对属于 SCA（软件成分分析），非 semgrep 模式匹配范畴；"
    "需引入专用 SCA 工具（如 Trivy/Grype）扫描 CocoaPods/SPM/Carthage 依赖或 SBOM，而非自写 semgrep 规则"
)

JUDGMENTS = {
    # ============ Android ============
    # --- AUTH：生物识别，MASTG 官方规则精确命中 ---
    "MASTG-TEST-0326": ("yes", ""),  # mastg-android-biometric-device-credential-fallback.yml
    "MASTG-TEST-0327": ("yes", ""),  # mastg-android-biometric-event-bound.yml
    "MASTG-TEST-0328": ("yes", ""),  # mastg-android-biometric-invalidated-enrollment.yml
    "MASTG-TEST-0329": ("yes", ""),  # mastg-android-biometric-no-confirmation-required.yml
    "MASTG-TEST-0330": ("yes", ""),  # mastg-android-biometric-validity-duration.yml

    # --- CODE ---
    "MASTG-TEST-0222": ("no", BIN_NOTE_ANDROID_PIC_CANARY),
    "MASTG-TEST-0223": ("no", BIN_NOTE_ANDROID_PIC_CANARY),
    "MASTG-TEST-0245": ("yes", ""),  # mastg-android-sdk-version.yml
    "MASTG-TEST-0272": ("no", SCA_NOTE_ANDROID),
    "MASTG-TEST-0274": ("no", SCA_NOTE_ANDROID),
    "MASTG-TEST-0337": ("yes", ""),  # mastg-android-object-deserialization.yml
    "MASTG-TEST-0339": ("yes", ""),  # mastg-android-sql-injection-contentprovider.yml
    "MASTG-TEST-0372": ("yes", ""),  # mastg-android-implicit-intent-internal-communication.yml
    "MASTG-TEST-0374": ("yes", ""),  # mastg-android-implicit-intent-leaking-extras.yml
    "MASTG-TEST-0398": ("yes", ""),  # mastg-android-webview-url-handlers.yml
    "MASTG-TEST-0399": ("yes", ""),  # mastg-android-webview-safebrowsing.yml

    # --- CRYPTO ---
    "MASTG-TEST-0204": ("yes", ""),  # mastg-android-random-apis-insufficient-entropy.yml
    "MASTG-TEST-0205": ("yes", ""),  # mastg-android-non-random-use.yml
    "MASTG-TEST-0208": ("yes", ""),  # mastg-android-key-generation-with-insufficient-key-length.yml
    "MASTG-TEST-0212": ("yes", ""),  # mastg-android-hardcoded-crypto-keys-usage.yml + mobsfscan hardcoded_*
    "MASTG-TEST-0221": ("yes", ""),  # mastg-android-broken-encryption-algorithms.yaml
    "MASTG-TEST-0232": ("yes", ""),  # mastg-android-broken-encryption-modes.yaml + mobsfscan cbc_padding_oracle
    "MASTG-TEST-0307": ("yes", ""),  # mastg-android-asymmetric-key-pair-used-for-multiple-purposes.yml
    "MASTG-TEST-0312": ("yes", ""),  # mastg-android-hardcoded-security-provider.yaml

    # --- NETWORK ---
    "MASTG-TEST-0234": ("yes", ""),  # mastg-android-ssl-socket-hostnameverifier.yml
    "MASTG-TEST-0242": ("yes", ""),  # mobsfscan android_ssl_pinning（网络安全配置证书锁定）
    "MASTG-TEST-0243": ("yes", ""),  # mobsfscan android_ssl_pinning（同一 pin 配置文件）
    "MASTG-TEST-0282": ("yes", ""),  # mastg-android-network-checkservertrusted.yml
    "MASTG-TEST-0283": ("yes", ""),  # mastg-android-network-hostname-verification.yml
    "MASTG-TEST-0284": ("yes", ""),  # mastg-android-network-onreceivedsslerror.yml
    "MASTG-TEST-0286": ("yes", ""),  # mastg-android-network-insecure-trust-anchors.yml

    # --- PLATFORM ---
    "MASTG-TEST-0252": ("yes", ""),  # mastg-android-webview-allow-local-access.yml
    "MASTG-TEST-0258": ("yes", ""),  # mastg-android-keyboard-cache-input-types.yml
    "MASTG-TEST-0291": ("yes", ""),  # mastg-android-sensitive-data-in-screenshot.yml
    "MASTG-TEST-0292": ("yes", ""),  # mastg-android-sensitive-data-in-screenshot.yml（同族）
    "MASTG-TEST-0293": ("yes", ""),  # mastg-android-sensitive-data-in-screenshot.yml（同族）
    "MASTG-TEST-0294": ("yes", ""),  # mastg-android-sensitive-data-in-screenshot.yml（同族）
    "MASTG-TEST-0315": ("yes", ""),  # mastg-android-sensitive-data-in-notifications(-manifest).yml
    "MASTG-TEST-0316": ("yes", ""),  # mastg-android-input-field-usage.yml
    "MASTG-TEST-0334": ("yes", ""),  # mastg-android-webview-bridges.yml + mobsfscan webview_javascript_interface
    "MASTG-TEST-0340": ("yes", ""),  # mastg-android-overlay-protection.yml
    "MASTG-TEST-0355": ("yes", ""),  # mastg-android-content-provider-exported.yml
    "MASTG-TEST-0357": ("yes", ""),  # mastg-android-fileprovider-broad-scope.yml
    "MASTG-TEST-0381": ("yes", ""),  # mastg-android-pendingintent-mutable.yml
    "MASTG-TEST-0393": ("yes", ""),  # mastg-android-deeplink-autoverify-missing.yml
    "MASTG-TEST-0394": ("yes", ""),  # mastg-android-deeplink-unvalidated-parameter.yml / custom-deeplink-scheme.yml

    # --- PRIVACY ---
    "MASTG-TEST-0254": ("yes", ""),  # mastg-android-dangerous-app-permissions.yaml

    # --- RESILIENCE ---
    "MASTG-TEST-0224": (
        "no",
        "需对已签名 APK 做二进制层校验（apksigner verify），非源码 semgrep 可覆盖；"
        "需自写脚本调用 apksigner/keytool 检测签名方案版本",
    ),
    "MASTG-TEST-0225": (
        "no",
        "需对已签名 APK 做二进制层校验，非源码 semgrep 可覆盖；"
        "需自写脚本调用 apksigner/keytool 检测签名证书密钥长度",
    ),
    "MASTG-TEST-0226": ("yes", ""),  # mastg-android-debuggable-flag.yml
    "MASTG-TEST-0247": ("yes", ""),  # mastg-android-device-passcode-present.yml
    "MASTG-TEST-0265": ("yes", ""),  # mastg-android-strictmode.yml
    "MASTG-TEST-0288": (
        "no",
        "需对 native .so 二进制做符号表检查（nm/strip 校验），非源码模式匹配；需自写二进制检测脚本",
    ),
    "MASTG-TEST-0324": ("yes", ""),  # mastg-android-root-detection.yaml + mobsfscan android_root_detection
    "MASTG-TEST-0338": ("yes", ""),  # mobsfscan android_safetynet（存储完整性/证明 API）
    "MASTG-TEST-0352": ("yes", ""),  # mastg-android-debugger-checks.yml / native-debugger-checks.yml
    "MASTG-TEST-0369": (
        "no",
        "需对 native 二进制做逆向/符号混淆度评估，非 semgrep 源码规则可覆盖；"
        "需自写原生二进制分析脚本或引入专用逆向评估工具",
    ),

    # --- STORAGE ---
    "MASTG-TEST-0231": ("yes", ""),  # mobsfscan android_logging / android_kotlin_logging
    "MASTG-TEST-0262": ("yes", ""),  # mastg-android-backup-manifest.yml + mobsfscan allow_backup

    # ============ iOS ============
    # --- AUTH：mobsfscan ios_biometric_acl ---
    "MASTG-TEST-0266": ("yes", ""),
    "MASTG-TEST-0268": ("yes", ""),
    "MASTG-TEST-0270": ("yes", ""),

    # --- CODE ---
    "MASTG-TEST-0228": ("no", BIN_NOTE_IOS_PIC_CANARY),
    "MASTG-TEST-0229": ("no", BIN_NOTE_IOS_PIC_CANARY),
    "MASTG-TEST-0230": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0273": ("no", SCA_NOTE_IOS),
    "MASTG-TEST-0275": ("no", SCA_NOTE_IOS),
    "MASTG-TEST-0383": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0386": ("partial", IOS_OBJC_PARTIAL_NOTE),

    # --- CRYPTO：ios_hardcoded_secret 精确命中；其余无对应 bullet，只能 partial ---
    "MASTG-TEST-0209": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0210": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0211": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0213": ("yes", ""),  # mobsfscan ios_hardcoded_secret
    "MASTG-TEST-0214": ("yes", ""),  # mobsfscan ios_hardcoded_secret
    "MASTG-TEST-0311": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0317": ("partial", IOS_OBJC_PARTIAL_NOTE),

    # --- NETWORK：ios_cert_pinning 精确命中证书锁定族；其余无对应 bullet ---
    "MASTG-TEST-0321": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0322": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0323": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0342": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0343": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0344": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0345": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0385": ("yes", ""),  # mobsfscan ios_cert_pinning
    "MASTG-TEST-0396": ("yes", ""),  # mobsfscan ios_cert_pinning（证书校验绕过同族）
    "MASTG-TEST-0397": ("yes", ""),  # mobsfscan ios_cert_pinning（证书校验绕过同族）

    # --- PLATFORM：ios_load_html_string 精确命中 WebView URL 加载；其余无对应 bullet ---
    "MASTG-TEST-0276": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0278": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0279": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0280": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0331": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0332": ("yes", ""),  # mobsfscan ios_load_html_string
    "MASTG-TEST-0333": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0335": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0346": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0370": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0371": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0376": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0377": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0378": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0379": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0380": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0389": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0390": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0395": ("partial", IOS_OBJC_PARTIAL_NOTE),

    # --- PRIVACY ---
    "MASTG-TEST-0281": (
        "no",
        "需比对已知第三方追踪域名库（隐私清单审计），非 semgrep 模式匹配范畴；"
        "需引入专用隐私清单/追踪域名库比对工具，而非自写 semgrep 规则",
    ),
    "MASTG-TEST-0360": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0362": ("partial", IOS_OBJC_PARTIAL_NOTE),

    # --- RESILIENCE ---
    "MASTG-TEST-0219": (
        "no",
        "需对二进制做符号表检查（nm/strip 校验），非源码模式匹配；需自写二进制检测脚本",
    ),
    "MASTG-TEST-0220": (
        "no",
        "需 codesign 工具检验二进制签名格式，非源码规则可覆盖；需自写脚本调用 codesign 检测",
    ),
    "MASTG-TEST-0240": ("yes", ""),  # mobsfscan ios_jailbreak_detect
    "MASTG-TEST-0248": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0261": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0358": ("yes", ""),  # mobsfscan ios_app_logging / ios_log
    "MASTG-TEST-0387": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0391": (
        "no",
        "需对 native 二进制做混淆度评估/逆向分析，非 semgrep 源码规则可覆盖；需自写原生二进制分析脚本",
    ),
    "MASTG-TEST-0401": ("yes", ""),  # mobsfscan ios_detect_reversing

    # --- STORAGE ---
    "MASTG-TEST-0215": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0297": ("yes", ""),  # mobsfscan ios_app_logging / ios_log
    "MASTG-TEST-0300": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0303": ("partial", IOS_OBJC_PARTIAL_NOTE),
    "MASTG-TEST-0313": ("yes", ""),  # mobsfscan ios_keyboard_cache
    "MASTG-TEST-0388": ("partial", IOS_OBJC_PARTIAL_NOTE),
}


def main():
    with open(IN, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        ready_rule, gap_note = JUDGMENTS.get(r["id"], DEFAULT)
        r["ready_rule"] = ready_rule
        r["gap_note"] = gap_note
        # 原生静态检查都有 CLI 工具可跑（含 libsast、含待补的自写原生规则），一律保持 yes
        r["ci_feasible"] = "yes"

    fields = list(rows[0].keys())
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    n_yes = sum(1 for r in rows if r["ready_rule"] == "yes")
    n_partial = sum(1 for r in rows if r["ready_rule"] == "partial")
    n_no = sum(1 for r in rows if r["ready_rule"] == "no")
    print(f"标注 {len(rows)} 行 → {OUT}")
    print(f"ready_rule: yes={n_yes} partial={n_partial} no={n_no}")


if __name__ == "__main__":
    main()
