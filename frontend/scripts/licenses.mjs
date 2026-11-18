// Include dependency license texts alongside the distributed browser assets.
import { execFileSync } from "node:child_process";
import { readFileSync, readdirSync, mkdirSync, writeFileSync } from "node:fs";
const directories = execFileSync(
  "npm",
  ["ls", "--omit=dev", "--all", "--parseable"],
  { encoding: "utf8" },
)
  .trim()
  .split("\n")
  .slice(1);
const sections = [];
for (const directory of directories) {
  const metadata = JSON.parse(
    readFileSync(`${directory}/package.json`, "utf8"),
  );
  const files = readdirSync(directory).filter((name) =>
    /^(licen[cs]e|copying|notice)(\.|$)/i.test(name),
  );
  const texts = files
    .map((name) => {
      try {
        return readFileSync(`${directory}/${name}`, "utf8");
      } catch {
        return "";
      }
    })
    .filter(Boolean);
  sections.push(
    `${metadata.name}@${metadata.version}\nLicense: ${typeof metadata.license === "string" ? metadata.license : JSON.stringify(metadata.license)}\n${texts.join("\n")}`,
  );
}
mkdirSync("public", { recursive: true });
writeFileSync(
  "public/third-party-licenses.txt",
  sections.join("\n\n" + "=".repeat(72) + "\n\n"),
);
