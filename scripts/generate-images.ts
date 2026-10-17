/**
 * Generates the marketing illustrations through OpenRouter (an image-output model).
 *
 *   bun scripts/generate-images.ts            # all images
 *   bun scripts/generate-images.ts hero-home  # one image by name
 *
 * The API key is read from backend/.env at run time and is never printed. Images are
 * written to public/media/generated. Each prompt asks for no text, no logos and no real
 * people, so the art can sit next to real product screens without implying customers.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = resolve(import.meta.dirname, "..");
const OUT = resolve(ROOT, "public/media/generated");
const MODEL = process.env["IMAGE_MODEL"] ?? "google/gemini-2.5-flash-image";

const STYLE =
  "Premium modern SaaS marketing illustration. Clean 3D-rendered shapes with soft studio lighting, " +
  "smooth gradients in deep navy (#0b1426) and brand blue (#155dfc) with subtle violet accents, " +
  "generous negative space, crisp edges, minimal detail. Absolutely no text, letters, numbers, logos, " +
  "watermarks or human faces.";

const IMAGES: Record<string, { size: string; prompt: string }> = {
  "hero-home": {
    size: "16:9",
    prompt:
      "A glowing blue orb of soft light at the centre, with rounded chat-bubble shapes flowing into a " +
      "floating glass panel that holds a neat document stack and a checkmark. Dark navy background.",
  },
  "hero-product": {
    size: "16:9",
    prompt:
      "A laptop-sized glass browser window floating above a dark navy surface, showing abstract chat " +
      "bubbles and a small document card, with light rays in brand blue.",
  },
  "feature-widget": {
    size: "4:3",
    prompt:
      "A website browser page with a round chat launcher bubble glowing in the bottom-right corner. Light, airy composition.",
  },
  "feature-knowledge": {
    size: "4:3",
    prompt:
      "Several document sheets fanning out into a single glowing answer card with a small citation tag. Light background.",
  },
  "feature-inbox": {
    size: "4:3",
    prompt:
      "A stack of rounded conversation cards arranged neatly in a tray, one highlighted in brand blue. Light background.",
  },
  "feature-leads": {
    size: "4:3",
    prompt:
      "A circular progress ring with three rising bars beside it, suggesting lead scoring. Light background.",
  },
  "use-dental": {
    size: "4:3",
    prompt:
      "A calm clinic reception desk with a tooth-shaped icon and a speech bubble, soft morning light.",
  },
  "use-plumbing": {
    size: "4:3",
    prompt: "A wrench and a water droplet beside a map pin and a small phone with a chat bubble.",
  },
  "use-fitness": {
    size: "4:3",
    prompt: "A dumbbell and a calendar card with a checked slot, arranged as a clean composition.",
  },
  "use-shop": {
    size: "4:3",
    prompt: "A shopping bag and a delivery parcel with a chat bubble that carries a tick.",
  },
  "use-legal": {
    size: "4:3",
    prompt: "A balance scale above a stack of folders, with a small intake form card.",
  },
  "use-letting": {
    size: "4:3",
    prompt: "A house silhouette with a key and a viewing calendar card.",
  },
  "solution-support": {
    size: "4:3",
    prompt:
      "A help-centre book open with a glowing question mark rising from it and a chat bubble.",
  },
  "solution-leads": {
    size: "4:3",
    prompt: "A funnel made of glass panels turning many small dots into a few bright glowing ones.",
  },
  "solution-sales": {
    size: "4:3",
    prompt: "A rising line made of soft light over a grid of tiles, suggesting pipeline progress.",
  },
  "solution-small": {
    size: "4:3",
    prompt: "A small storefront with an open sign glowing softly and a chat bubble above the door.",
  },
  "about-mission": {
    size: "16:9",
    prompt:
      "An abstract horizon with a path of light leading toward a rising sun, calm and optimistic.",
  },
};

function apiKey(): string {
  const env = readFileSync(resolve(ROOT, "backend/.env"), "utf-8");
  const line = env.split("\n").find((l) => l.startsWith("OPENROUTER_API_KEY="));
  const key = line?.slice("OPENROUTER_API_KEY=".length).trim() ?? "";
  if (!key) throw new Error("OPENROUTER_API_KEY is not set in backend/.env");
  return key;
}

async function generate(name: string, prompt: string, key: string): Promise<void> {
  const target = resolve(OUT, `${name}.png`);
  if (existsSync(target)) {
    console.log("skip (exists)", name);
    return;
  }
  const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://oraone.in",
      "X-Title": "OraOne",
    },
    body: JSON.stringify({
      model: MODEL,
      modalities: ["image", "text"],
      messages: [{ role: "user", content: `${STYLE}\n\n${prompt}` }],
    }),
  });
  if (!res.ok) throw new Error(`${name}: HTTP ${res.status} ${(await res.text()).slice(0, 200)}`);
  const body = (await res.json()) as {
    choices: { message: { images?: { image_url: { url: string } }[] } }[];
  };
  const url = body.choices[0]?.message.images?.[0]?.image_url.url;
  if (!url) throw new Error(`${name}: no image in response`);
  const base64 = url.split(",")[1];
  if (!base64) throw new Error(`${name}: unexpected image format`);
  writeFileSync(target, Buffer.from(base64, "base64"));
  console.log("generated", name);
}

async function main() {
  mkdirSync(OUT, { recursive: true });
  const key = apiKey();
  const only = process.argv[2];
  const names = only ? [only] : Object.keys(IMAGES);
  for (const name of names) {
    const spec = IMAGES[name];
    if (!spec) throw new Error(`unknown image ${name}`);
    await generate(name, spec.prompt, key);
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
