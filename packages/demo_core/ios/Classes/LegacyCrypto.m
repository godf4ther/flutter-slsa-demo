#import "LegacyCrypto.h"

@implementation LegacyCrypto

// [FIX] 不再硬编码 secret/password，改为运行时从环境/安全存储读取
- (NSString *)apiSecret {
    return [[NSProcessInfo processInfo] environment][@"API_SECRET"];
}

- (NSString *)legacyPassword {
    return [[NSProcessInfo processInfo] environment][@"LEGACY_PASSWORD"];
}

@end
