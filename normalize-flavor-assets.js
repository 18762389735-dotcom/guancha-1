const fs = require("fs");
const path = require("path");
const { createCanvas, loadImage } = require("@napi-rs/canvas");

const sourceDir = path.join(__dirname, "assets", "flavors");
const outputDir = path.join(__dirname, "assets", "flavors-normalized");
const canvasSize = 512;

fs.mkdirSync(outputDir, { recursive: true });

function removeNeutralBackground(imageData) {
  const { data } = imageData;
  for (let index = 0; index < data.length; index += 4) {
    const red = data[index];
    const green = data[index + 1];
    const blue = data[index + 2];
    const alpha = data[index + 3];
    const maximum = Math.max(red, green, blue);
    const minimum = Math.min(red, green, blue);
    const luminance = red * 0.2126 + green * 0.7152 + blue * 0.0722;
    const isNeutral = maximum - minimum < 20;

    // 清除白底、浅灰底和浅灰网点；深色线稿仍保留。
    if (alpha > 0 && isNeutral && luminance > 118) data[index + 3] = 0;
  }
  return imageData;
}

async function normalize(fileName) {
  const image = await loadImage(path.join(sourceDir, fileName));
  const canvas = createCanvas(canvasSize, canvasSize);
  const context = canvas.getContext("2d");
  const scale = Math.min((canvasSize * 0.88) / image.width, (canvasSize * 0.88) / image.height);
  const width = image.width * scale;
  const height = image.height * scale;

  context.drawImage(image, (canvasSize - width) / 2, (canvasSize - height) / 2, width, height);
  const pixels = context.getImageData(0, 0, canvasSize, canvasSize);
  context.putImageData(removeNeutralBackground(pixels), 0, 0);
  fs.writeFileSync(path.join(outputDir, fileName), canvas.toBuffer("image/png"));
}

Promise.all(
  fs.readdirSync(sourceDir).filter((fileName) => fileName.toLowerCase().endsWith(".png")).map(normalize),
).then(() => console.log("Normalized flavor assets: done"));
