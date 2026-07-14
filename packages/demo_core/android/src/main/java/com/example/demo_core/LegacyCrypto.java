package com.example.demo_core;

import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;

/**
 * 模拟"核心 SDK"的遗留 Java 加密工具。
 * 故意埋入 MASTG 静态检查项对应的漏洞。
 */
public class LegacyCrypto {

    // [VULN] 硬编码口令 —— MASTG-TEST-0212 (Hardcoded Credentials)
    // mobsfscan: hardcoded_password
    private static final String PASSWORD = "SuperSecret123!";

    // [VULN] DES 弱算法 + ECB 弱模式 —— MASTG-TEST-0221/0232 (Broken Encryption Algorithms/Modes)
    // MASTG semgrep: mastg-android-broken-encryption-algorithms / -modes
    public byte[] encryptLegacy(byte[] data, byte[] key) throws Exception {
        Cipher cipher = Cipher.getInstance("DES/ECB/PKCS5Padding");
        SecretKeySpec keySpec = new SecretKeySpec(key, "DES");
        cipher.init(Cipher.ENCRYPT_MODE, keySpec);
        return cipher.doFinal(data);
    }

    public String getPassword() {
        return PASSWORD;
    }
}
