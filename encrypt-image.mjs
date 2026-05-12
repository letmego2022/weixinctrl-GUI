#!/usr/bin/env node
/**
 * 官方加密算法的 Node.js 实现
 * 用法: node encrypt-image.js <图片路径>
 * 输出: JSON { filekey, aeskey_hex, ciphertext_base64, filesize, rawsize }
 */
import crypto from "node:crypto";
import fs from "node:fs";

const filePath = process.argv[2];
if (!filePath) {
  console.error("用法: node encrypt-image.js <图片路径>");
  process.exit(1);
}

const plaintext = fs.readFileSync(filePath);
const rawsize = plaintext.length;
const rawfilemd5 = crypto.createHash("md5").update(plaintext).digest("hex");

// 生成 keys
const filekey = crypto.randomBytes(16).toString("hex");
const aeskey = crypto.randomBytes(16);

// AES-128-ECB PKCS7 padding（官方算法）
function aesEcbPaddedSize(size) {
  return Math.ceil((size + 1) / 16) * 16;
}

const filesize = aesEcbPaddedSize(rawsize);
const cipher = crypto.createCipheriv("aes-128-ecb", aeskey, null);
const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);

const result = {
  filekey,
  aeskey_hex: aeskey.toString("hex"),
  // Format B: base64(hex string) - 官方 openclaw 出站媒体使用的格式
  aeskey_base64: Buffer.from(aeskey.toString("hex")).toString("base64"),
  ciphertext_base64: ciphertext.toString("base64"),
  filesize,
  rawsize,
  rawfilemd5,
};

process.stdout.write(JSON.stringify(result));
