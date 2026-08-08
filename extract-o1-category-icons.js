const fs = require("fs");
const path = require("path");
const { createCanvas, loadImage } = require("@napi-rs/canvas");

const source = "C:/Users/QQ/Desktop/项目进度/美术资产/ui/o1-1.png";
const outputDir = path.join(__dirname, "assets", "o1-category-icons");
const crops = {
  tea: [84, 418, 102, 102],
  coffee: [84, 610, 102, 102],
  milk: [84, 804, 102, 102],
  juice: [84, 996, 102, 102],
};

fs.mkdirSync(outputDir, { recursive: true });

loadImage(source).then((reference) => {
  Object.entries(crops).forEach(([name, [x, y, width, height]]) => {
    const canvas = createCanvas(width, height);
    const context = canvas.getContext("2d");
    context.drawImage(reference, x, y, width, height, 0, 0, width, height);
    fs.writeFileSync(path.join(outputDir, `${name}.png`), canvas.toBuffer("image/png"));
  });
  console.log("O1 category icons extracted: done");
});
