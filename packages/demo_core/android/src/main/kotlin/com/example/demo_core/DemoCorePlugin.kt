package com.example.demo_core

import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * 模拟"核心 SDK"的 Kotlin 侧密钥/加密逻辑（已按 MASTG 建议修复）。
 */
class DemoCorePlugin {

    // [FIX] 密钥不再硬编码，由调用方从安全存储（Android Keystore / secure_storage）注入
    private var encryptionKey: ByteArray = ByteArray(0)

    fun setKey(key: ByteArray) {
        encryptionKey = key
    }

    // [FIX] 用密码学安全的 SecureRandom 生成 nonce
    fun generateNonce(): ByteArray {
        val random = SecureRandom()
        val nonce = ByteArray(12)
        random.nextBytes(nonce)
        return nonce
    }

    // [FIX] AES/GCM/NoPadding（认证加密）+ 随机 IV，替换 CBC + 确定性 IV
    fun encrypt(plain: ByteArray): ByteArray {
        val iv = generateNonce()
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        val keySpec = SecretKeySpec(encryptionKey, "AES")
        val spec = GCMParameterSpec(128, iv)
        cipher.init(Cipher.ENCRYPT_MODE, keySpec, spec)
        val cipherText = cipher.doFinal(plain)
        return iv + cipherText
    }
}
