#!/usr/bin/env bash
# 本地一次性引导：
#   1) iOS：可写 match 创建并加密证书/profile，推到私有证书仓库（CI 之后 readonly 复用）。
#   2) Android：keytool 生成 upload keystore，输出 base64 供填入 GitHub secret。
#
# 用法（先 export 一组环境变量）：
#   export APP_IDENTIFIER=io.slsa.flutterdemo
#   export FASTLANE_USER=you@apple.id
#   export FASTLANE_TEAM_ID=ABCDE12345
#   export MATCH_GIT_URL=https://github.com/<you>/flutter-slsa-demo-certs.git
#   export MATCH_PASSWORD='强口令'
#   # 可选：自定义 Android keystore 密码（默认 changeit，建议设强口令并与 GitHub secret 一致）
#   export ANDROID_KEYSTORE_PASSWORD='强口令' ANDROID_KEY_PASSWORD='强口令'
#   ./scripts/bootstrap-local.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> 检查必需环境变量"
: "${APP_IDENTIFIER:?需要 APP_IDENTIFIER}"
: "${FASTLANE_USER:?需要 FASTLANE_USER（Apple ID 邮箱）}"
: "${FASTLANE_TEAM_ID:?需要 FASTLANE_TEAM_ID}"
: "${MATCH_GIT_URL:?需要 MATCH_GIT_URL（私有证书仓库）}"
: "${MATCH_PASSWORD:?需要 MATCH_PASSWORD}"

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
