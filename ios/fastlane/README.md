fastlane documentation
----

# Installation

Make sure you have the latest version of the Xcode command line tools installed:

```sh
xcode-select --install
```

For _fastlane_ installation instructions, see [Installing _fastlane_](https://docs.fastlane.tools/#installing-fastlane)

# Available Actions

## iOS

### ios setup_signing

```sh
[bundle exec] fastlane ios setup_signing
```

下载签名证书与 profile（CI 中 readonly，不登录 Developer Portal）

### ios build

```sh
[bundle exec] fastlane ios build
```

构建签名 .ipa（gym 接管 archive + 签名 + export）

### ios upload

```sh
[bundle exec] fastlane ios upload
```

上传 .ipa 到 TestFlight（Apple ID + app-specific password，绕过 2FA，不提审上架）

----

This README.md is auto-generated and will be re-generated every time [_fastlane_](https://fastlane.tools) is run.

More information about _fastlane_ can be found on [fastlane.tools](https://fastlane.tools).

The documentation of _fastlane_ can be found on [docs.fastlane.tools](https://docs.fastlane.tools).
