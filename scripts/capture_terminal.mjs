#!/usr/bin/env node
/** Capture the terminal-style HTML pages at 2x for crisp screenshots. */
import { writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const PORT = 9222;
const SHOTS = [
  ["docs/api-success.html", "docs/screenshots/api-success.png"],
  ["docs/api-validation-400.html", "docs/screenshots/api-validation-400.png"],
  ["docs/api-persistence.html", "docs/screenshots/api-persistence.png"]
];

const targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const target = targets.find((item) => item.type === "page");
if (!target) throw new Error("No page target");

const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  ws.addEventListener("open", resolve, { once: true });
  ws.addEventListener("error", reject, { once: true });
});

let seq = 0;
const pending = new Map();
ws.addEventListener("message", (event) => {
  const message = JSON.parse(typeof event.data === "string" ? event.data : String(event.data));
  if (!message.id) return;
  const item = pending.get(message.id);
  if (!item) return;
  pending.delete(message.id);
  clearTimeout(item.timer);
  if (message.error) item.reject(new Error(`${message.error.message} (${message.error.code})`));
  else item.resolve(message.result);
});

function call(method, params = {}, timeout = 30000) {
  const id = ++seq;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`timeout ${method}`));
    }, timeout);
    pending.set(id, { resolve, reject, timer });
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  const result = await call("Runtime.evaluate", { expression, returnByValue: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || "evaluate failed");
  return result.result.value;
}

await call("Page.enable");
await call("Runtime.enable");

for (const [html, png] of SHOTS) {
  const url = `file:///${path.resolve(process.cwd(), html).replaceAll("\\", "/")}`;
  await call("Emulation.setDeviceMetricsOverride", {
    width: 1500, height: 900, deviceScaleFactor: 2, mobile: false, screenWidth: 1500, screenHeight: 900
  });
  await call("Page.navigate", { url });
  await new Promise((resolve) => setTimeout(resolve, 900));
  const height = Math.ceil(await evaluate("document.documentElement.scrollHeight"));
  await call("Emulation.setDeviceMetricsOverride", {
    width: 1500, height, deviceScaleFactor: 2, mobile: false, screenWidth: 1500, screenHeight: height
  });
  await new Promise((resolve) => setTimeout(resolve, 350));
  const shot = await call("Page.captureScreenshot", { format: "png", fromSurface: true }, 60000);
  const buffer = Buffer.from(shot.data, "base64");
  await writeFile(path.resolve(process.cwd(), png), buffer);
  console.log(`${png} ${1500}x${height} -> ${buffer.length} bytes`);
}

ws.close();
