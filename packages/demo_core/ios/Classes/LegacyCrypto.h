#import <Foundation/Foundation.h>

/// 模拟"核心 SDK"的遗留 Objective-C 部分（用于验证 mobsfscan libsast 对 ObjC 的覆盖）。
@interface LegacyCrypto : NSObject

- (NSString *)apiSecret;
- (NSString *)legacyPassword;

@end
