/**
 * Re-encodes the generated PNG illustrations to WebP through Chromium's canvas, which keeps
 * the marketing pages light without an extra image library. Run after generate-images.
 */
import { readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { chromium } from "@playwright/test";

const DIR = resolve(import.meta.dirname, "../public/media/generated");

async function main() {
  const files = readdirSync(DIR).filter((f) => f.endsWith(".png"));
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const file of files) {
    const data = readFileSync(resolve(DIR, file)).toString("base64");
    const webp = await page.evaluate(async (b64) => {
      const img = new Image();
      img.src = `data:image/png;base64,${b64}`;
      await img.decode();
      const canvas = document.createElement("canvas");
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      canvas.getContext("2d")!.drawImage(img, 0, 0);
      const url = canvas.toDataURL("image/webp", 0.86);
      return url.split(",")[1];
    }, data);
    writeFileSync(resolve(DIR, file.replace(/\.png$/, ".webp")), Buffer.from(webp, "base64"));
    rmSync(resolve(DIR, file));
    console.log("encoded", file.replace(/\.png$/, ".webp"));
  }
  await browser.close();
}

main();
