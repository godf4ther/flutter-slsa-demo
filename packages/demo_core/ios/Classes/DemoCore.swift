import Foundation
import CommonCrypto

/// 模拟"核心 SDK"的 Swift 侧逻辑（已按 MASTG 建议修复）。
class DemoCore {

    // [FIX] 密钥不再硬编码，由外部（Keychain / secure_storage）注入
    private var secretKey: Data = Data()

    func setKey(_ key: Data) {
        secretKey = key
    }

    // [FIX] 用 SHA-256 替换 MD5
    func sha256Hex(_ data: Data) -> String {
        var digest = [UInt8](repeating: 0, count: Int(CC_SHA256_DIGEST_LENGTH))
        data.withUnsafeBytes { ptr in
            _ = CC_SHA256(ptr.baseAddress, CC_LONG(data.count), &digest)
        }
        return digest.map { String(format: "%02x", $0) }.joined()
    }
}
