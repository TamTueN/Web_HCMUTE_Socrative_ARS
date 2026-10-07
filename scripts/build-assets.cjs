const fs = require("fs");
const path = require("path");
const { compile } = require("@tailwindcss/node");
const { Scanner } = require("@tailwindcss/oxide");

const root = path.resolve(__dirname, "..");
const staticDir = path.join(root, "static");
const vendorDir = path.join(staticDir, "vendor");
const fontAwesomeSource = path.join(
  root,
  "node_modules",
  "@fortawesome",
  "fontawesome-free"
);

function copyDirectory(source, destination) {
  fs.mkdirSync(destination, { recursive: true });
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const sourcePath = path.join(source, entry.name);
    const destinationPath = path.join(destination, entry.name);
    if (entry.isDirectory()) copyDirectory(sourcePath, destinationPath);
    else fs.copyFileSync(sourcePath, destinationPath);
  }
}

fs.mkdirSync(path.join(staticDir, "css"), { recursive: true });
fs.mkdirSync(path.join(vendorDir, "fontawesome"), { recursive: true });
fs.copyFileSync(
  path.join(fontAwesomeSource, "css", "all.min.css"),
  path.join(vendorDir, "fontawesome", "all.min.css")
);
copyDirectory(
  path.join(fontAwesomeSource, "webfonts"),
  path.join(vendorDir, "fontawesome", "webfonts")
);
fs.copyFileSync(
  path.join(root, "node_modules", "chart.js", "dist", "chart.umd.js"),
  path.join(vendorDir, "chart.umd.js")
);

async function resolveCssImport(id, base) {
  const candidate = id === "tailwindcss"
    ? path.join(root, "node_modules", "tailwindcss", "index.css")
    : path.resolve(base, id);
  return fs.existsSync(candidate) ? candidate : undefined;
}

async function buildCss() {
  const input = path.join(root, "assets", "css", "tailwind.css");
  const compiled = await compile(fs.readFileSync(input, "utf8"), {
    base: root,
    from: input,
    onDependency() {},
    customCssResolver: resolveCssImport
  });
  const scanner = new Scanner({
    sources: [{
      base: path.join(root, "templates"),
      pattern: "**/*.html",
      negated: false
    }]
  });
  const candidates = scanner.scan();
  if (candidates.length === 0) {
    throw new Error("Tailwind did not find any candidates in templates.");
  }

  const css = compiled.build(candidates);
  for (const utility of [".hidden", ".bg-blue-600", ".rounded-2xl"]) {
    if (!css.includes(`${utility} {`)) {
      throw new Error(`Generated Tailwind CSS is missing ${utility}.`);
    }
  }
  fs.writeFileSync(path.join(staticDir, "css", "app.css"), css);
}

buildCss().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
