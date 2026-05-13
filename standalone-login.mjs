#!/usr/bin/env node
/**
 * 独立微信扫码登录 - 不需要 openclaw
 * 直接调用 ilink API 完成扫码登录
 */
import https from "node:https";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";

// ── 常量 ────────────────────────────────────────────────────────────────────
const FIXED_BASE_URL = "https://ilinkai.weixin.qq.com";
const BOT_TYPE = "3";
const STATE_DIR = path.join(os.homedir(), ".openclaw", "openclaw-weixin");
const ACCOUNTS_DIR = path.join(STATE_DIR, "accounts");
const CONFIG_FILE = path.join(STATE_DIR, "config.json");

// 来自插件 package.json 的 ilink_appid
const ILINK_APP_ID = "bot";
// 插件版本
const CHANNEL_VERSION = "2.1.8";

function buildClientVersion(version) {
  const parts = version.split(".").map((p) => parseInt(p, 10));
  const major = parts[0] ?? 0;
  const minor = parts[1] ?? 0;
  const patch = parts[2] ?? 0;
  return ((major & 0xff) << 16) | ((minor & 0xff) << 8) | (patch & 0xff);
}
const ILINK_APP_CLIENT_VERSION = buildClientVersion(CHANNEL_VERSION);

// ── HTTP 工具 ────────────────────────────────────────────────────────────────
function httpGet(url, headers = {}) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const opts = {
      hostname: u.hostname,
      path: u.pathname + u.search,
      method: "GET",
      headers: {
        ...headers,
        "iLink-App-Id": ILINK_APP_ID,
        "iLink-App-ClientVersion": String(ILINK_APP_CLIENT_VERSION),
      },
    };
    const req = https.request(opts, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        try {
          resolve(JSON.parse(data));
        } catch {
          resolve(data);
        }
      });
    });
    req.on("error", reject);
    req.setTimeout(40000, () => {
      req.destroy();
      reject(new Error("请求超时"));
    });
    req.end();
  });
}

function randomUint32Base64() {
  const uint32 = crypto.randomBytes(4).readUInt32BE(0);
  return Buffer.from(String(uint32), "utf-8").toString("base64");
}

// ── 核心 API ──────────────────────────────────────────────────────────────────
async function fetchQRCode() {
  const url = `${FIXED_BASE_URL}/ilink/bot/get_bot_qrcode?bot_type=${BOT_TYPE}`;
  const headers = { "X-WECHAT-UIN": randomUint32Base64() };
  console.log("[API] 获取二维码...");
  return httpGet(url, headers);
}

async function pollQRStatus(qrcode, baseUrl = FIXED_BASE_URL) {
  const encodedQr = encodeURIComponent(qrcode);
  const url = `${baseUrl}/ilink/bot/get_qrcode_status?qrcode=${encodedQr}`;
  const headers = { "X-WECHAT-UIN": randomUint32Base64() };
  try {
    return await httpGet(url, headers);
  } catch (e) {
    if (e.message === "请求超时") {
      return { status: "wait" };
    }
    throw e;
  }
}

// ── 终端二维码显示 ────────────────────────────────────────────────────────────
async function showQR(qrcodeUrl) {
  try {
    const qrcode = await import("qrcode");
    const terminal = await import("qrcode-terminal");
    terminal.default.generate(qrcodeUrl, { small: true });
  } catch {
    console.log("请用微信扫描以下二维码:");
    console.log(qrcodeUrl);
  }
}

// ── 保存账号 ──────────────────────────────────────────────────────────────────
function ensureDirs() {
  fs.mkdirSync(ACCOUNTS_DIR, { recursive: true });
}

function saveAccount(data) {
  ensureDirs();
  const accountId = data.accountId;
  const accountData = {
    account_id: accountId,
    user_id: data.userId,
    bot_token: data.botToken,
    base_url: data.baseUrl || FIXED_BASE_URL,
    login_time: new Date().toISOString(),
  };
  const accountFile = path.join(ACCOUNTS_DIR, `${accountId}.json`);
  fs.writeFileSync(accountFile, JSON.stringify(accountData, null, 2), "utf-8");

  const config = {
    current_account: accountId,
    accounts: [accountId],
  };
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2), "utf-8");

  console.log(`\n账号信息已保存到: ${accountFile}`);
  return accountFile;
}

// ── 登录主流程 ────────────────────────────────────────────────────────────────
async function login() {
  console.log("=".repeat(50));
  console.log("  微信扫码登录 (独立版 - 无需 openclaw)");
  console.log("=".repeat(50));
  console.log();

  // 1. 获取二维码
  let qrResp;
  try {
    qrResp = await fetchQRCode();
  } catch (e) {
    console.error("[错误] 无法获取二维码:", e.message);
    console.error("请检查网络连接，或确认 ilinkai.weixin.qq.com 可访问");
    process.exit(1);
  }

  if (qrResp.ret !== 0) {
    console.error("[错误] 获取二维码失败:", qrResp);
    process.exit(1);
  }

  const qrcode = qrResp.qrcode;
  const qrcodeUrl = qrResp.qrcode_img_content;

  console.log("二维码已获取!");
  console.log();
  await showQR(qrcodeUrl);
  console.log();
  console.log("请使用微信扫描二维码，并在微信中确认授权");
  console.log("(也可以用浏览器打开链接扫码)");
  console.log();

  // 2. 轮询扫码状态
  let currentBaseUrl = FIXED_BASE_URL;
  let expireCount = 0;
  const MAX_EXPIRE = 3;

  while (true) {
    let statusResp;
    try {
      statusResp = await pollQRStatus(qrcode, currentBaseUrl);
    } catch (e) {
      console.error("\n[错误] 轮询失败:", e.message);
      process.exit(1);
    }

    const status = statusResp.status;

    switch (status) {
      case "wait":
        process.stdout.write(".");
        break;
      case "scaned":
        process.stdout.write("\n[状态] 已扫码，请在微信确认...\n");
        break;
      case "scaned_but_redirect": {
        const redirectHost = statusResp.redirect_host;
        if (redirectHost) {
          currentBaseUrl = `https://${redirectHost}`;
          console.log(`[状态] 切换到: ${currentBaseUrl}`);
        }
        break;
      }
      case "expired":
        expireCount++;
        if (expireCount > MAX_EXPIRE) {
          console.error("\n[错误] 二维码多次过期，登录失败");
          process.exit(1);
        }
        console.log(`\n[状态] 二维码已过期，正在刷新... (${expireCount}/${MAX_EXPIRE})`);
        try {
          qrResp = await fetchQRCode();
          await showQR(qrResp.qrcode_img_content);
        } catch (e) {
          console.error("[错误] 刷新二维码失败:", e.message);
          process.exit(1);
        }
        break;
      case "confirmed": {
        const botToken = statusResp.bot_token;
        const ilinkBotId = statusResp.ilink_bot_id;
        const ilinkUserId = statusResp.ilink_user_id;
        const baseUrl = statusResp.baseurl || FIXED_BASE_URL;

        if (!ilinkBotId) {
          console.error("\n[错误] 登录确认但缺少 ilink_bot_id");
          process.exit(1);
        }

        console.log("\n" + "=".repeat(50));
        console.log("  ✅ 登录成功!");
        console.log("=".repeat(50));
        console.log(`  Bot ID:    ${ilinkBotId}`);
        console.log(`  User ID:   ${ilinkUserId}`);
        console.log(`  Token:     ${botToken ? botToken.substring(0, 20) + "..." : "无"}`);
        console.log(`  API URL:   ${baseUrl}`);

        saveAccount({
          accountId: ilinkBotId,
          userId: ilinkUserId,
          botToken: botToken,
          baseUrl: baseUrl,
        });

        console.log("\n现在可以用 Python client.py 接收消息了!");
        return;
      }
      default:
        process.stdout.write("?");
    }

    await new Promise((r) => setTimeout(r, 1000));
  }
}

login().catch((e) => {
  console.error("\n[错误]", e);
  process.exit(1);
});
