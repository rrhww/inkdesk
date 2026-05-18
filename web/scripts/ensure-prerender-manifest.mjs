import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

function randomHex(bytes) {
  return crypto.randomBytes(bytes).toString("hex");
}

async function ensurePrerenderManifest() {
  const nextDir = path.join(process.cwd(), ".next");
  const buildIdPath = path.join(nextDir, "BUILD_ID");
  const manifestPath = path.join(nextDir, "prerender-manifest.json");

  try {
    await fs.access(buildIdPath);
  } catch {
    return;
  }

  try {
    await fs.access(manifestPath);
    return;
  } catch {
    // Continue and create the manifest below.
  }

  const manifest = {
    version: 4,
    routes: {},
    dynamicRoutes: {},
    notFoundRoutes: [],
    preview: {
      previewModeId: randomHex(16),
      previewModeSigningKey: randomHex(32),
      previewModeEncryptionKey: randomHex(32)
    }
  };

  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  process.stdout.write(`[inkvault] created missing .next/prerender-manifest.json\n`);
}

await ensurePrerenderManifest();
