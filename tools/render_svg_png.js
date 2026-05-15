const fs = require("fs");
const path = require("path");
const { Resvg } = require("@resvg/resvg-js");

function usage() {
  console.error("Usage: node tools/render_svg_png.js <input.svg> <output.png> [scale]");
  process.exit(2);
}

const [, , inputArg, outputArg, scaleArg] = process.argv;
if (!inputArg || !outputArg) usage();

const input = path.resolve(inputArg);
const output = path.resolve(outputArg);
const scale = Number(scaleArg || "2");

const svg = fs.readFileSync(input);
const resvg = new Resvg(svg, {
  fitTo: {
    mode: "zoom",
    value: Number.isFinite(scale) && scale > 0 ? scale : 2,
  },
  font: {
    loadSystemFonts: true,
    defaultFontFamily: "Arial",
  },
});

const png = resvg.render().asPng();
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, png);

console.log(JSON.stringify({ input, output, scale, bytes: png.length }, null, 2));
