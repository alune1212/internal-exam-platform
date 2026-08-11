import { readdir, readFile } from "node:fs/promises";
import { extname, join } from "node:path";
import process from "node:process";
import { URL, fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../dist/", import.meta.url));
const textExtensions = new Set([".html", ".css", ".js", ".json", ".svg"]);
const forbidden = [
  { label: "external HTML asset", pattern: /(?:src|href)\s*=\s*["'](?:https?:)?\/\//i },
  { label: "external CSS asset", pattern: /url\(\s*["']?(?:https?:)?\/\//i },
  { label: "external CSS import", pattern: /@import\s+(?:url\()?\s*["']?(?:https?:)?\/\//i },
  { label: "external runtime fetch", pattern: /(?:fetch|new\s+URL)\(\s*["'](?:https?:)?\/\//i },
];

async function files(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map((entry) => {
      const path = join(directory, entry.name);
      return entry.isDirectory() ? files(path) : [path];
    }),
  );
  return nested.flat();
}

const failures = [];
for (const path of await files(root)) {
  if (!textExtensions.has(extname(path))) continue;
  const content = await readFile(path, "utf8");
  for (const rule of forbidden) {
    if (rule.pattern.test(content)) failures.push(`${path}: ${rule.label}`);
  }
}

if (failures.length) {
  throw new Error(`Built runtime contains external asset references:\n${failures.join("\n")}`);
}
process.stdout.write("offline_asset_check=passed external_runtime_references=0\n");
