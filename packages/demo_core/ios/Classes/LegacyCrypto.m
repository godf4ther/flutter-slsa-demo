#import "LegacyCrypto.h"

@implementation LegacyCrypto

// [VULN] 硬编码 API secret —— MASTG (Hardcoded Secret)。用于验证 mobsfscan libsast 对 ObjC 的覆盖。
NSString *const kApiSecret = @"objc_hardcoded_api_secret_abcdef123456";

- (NSString *)apiSecret {
    return kApiSecret;
}

// [VULN] 硬编码口令
- (NSString *)legacyPassword {
    NSString *password = @"ObjCLegacyPassword!2024";
    return password;
}

@end
