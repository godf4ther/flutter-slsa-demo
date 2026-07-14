package com.example.demo_core;

import java.security.SecureRandom;
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * 模拟"核心 SDK"的加密工具（已按 MASTG 建议修复）。
 */
public class LegacyCrypto {

    // [FIX] 直接持有 SecretKey（如从 Android Keystore 取），不接触原始密钥字节，
    // 也不通过 new SecretKeySpec(rawBytes) 构造——从源头避免硬编码密钥风险。
    private final SecretKey key;

    public LegacyCrypto(SecretKey key) {
        this.key = key;
    }

    // [FIX] AES/GCM 认证加密 + 随机 IV，替换 DES/ECB
    public byte[] encrypt(byte[] data) throws Exception {
        byte[] iv = new byte[12];
        new SecureRandom().nextBytes(iv);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(128, iv));
        byte[] cipherText = cipher.doFinal(data);
        byte[] out = new byte[iv.length + cipherText.length];
        System.arraycopy(iv, 0, out, 0, iv.length);
        System.arraycopy(cipherText, 0, out, iv.length, cipherText.length);
        return out;
    }
}
