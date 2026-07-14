import Foundation
import CommonCrypto

/// 模拟"核心 SDK"的 Swift 侧逻辑。故意埋入 MASTG 静态检查项对应的漏洞。
class DemoCore {

    // [VULN] 硬编码密钥 —— MASTG-TEST-0213/0214 (Hardcoded Cryptographic Keys)
    // mobsfscan: ios_hardcoded_secret
    private let secretKey = "hardcoded_swift_secret_key_9876"

    // [VULN] 弱哈希 MD5 —— MASTG (Weak Hashing)
    func md5Hex(_ data: Data) -> String {
        var digest = [UInt8](repeating: 0, count: Int(CC_MD5_DIGEST_LENGTH))
        data.withUnsafeBytes { ptr in
            _ = CC_MD5(ptr.baseAddress, CC_LONG(data.count), &digest)
        }
        return digest.map { String(format: "%02x", $0) }.joined()
    }

    func key() -> String {
        return secretKey
    }
}
