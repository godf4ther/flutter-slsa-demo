package com.example.demo_core

import java.util.Random
import javax.crypto.Cipher
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * 模拟"核心 SDK"的 Kotlin 侧密钥/加密逻辑。
 * 故意埋入 MASTG 静态检查项对应的漏洞，用于演示 CI 静态扫描能命中。
 */
class DemoCorePlugin {

    // [VULN] 硬编码加密密钥 —— MASTG-TEST-0212 (Use of Hardcoded Cryptographic Keys)
    // mobsfscan: android_kotlin_hardcoded
    private val encryptionKey = "hardcoded_aes_key_1234567890abcd"

    // [VULN] 用非密码学安全的 java.util.Random 生成 nonce —— MASTG-TEST-0204/0205 (Insecure Random)
    fun generateNonce(): ByteArray {
        val random = Random()
        val nonce = ByteArray(16)
        random.nextBytes(nonce)
        return nonce
    }

    // [VULN] AES/CBC/PKCS5 + 全零确定性 IV + 无完整性校验 —— MASTG-TEST-0232 (Broken Encryption Modes)
    // mobsfscan: cbc_kotlin_padding_oracle
    fun encrypt(plain: ByteArray): ByteArray {
        val cipher = Cipher.getInstance("AES/CBC/PKCS5Padding")
        val keySpec = SecretKeySpec(encryptionKey.toByteArray(), "AES")
        val iv = IvParameterSpec(ByteArray(16))
        cipher.init(Cipher.ENCRYPT_MODE, keySpec, iv)
        return cipher.doFinal(plain)
    }
}
