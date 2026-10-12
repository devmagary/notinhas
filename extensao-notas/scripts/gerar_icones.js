// Gera icones PNG basicos (16x16, 48x48, 128x128) para a extensao usando zlib nativo do Node
const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

function criarPNG(largura, altura, r, g, b) {
  // Assinatura PNG
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

  // Chunk IHDR
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(largura, 0);
  ihdr.writeUInt32BE(altura, 4);
  ihdr.writeUInt8(8, 8); // bit depth 8
  ihdr.writeUInt8(2, 9); // color type 2 (RGB)
  ihdr.writeUInt8(0, 10); // compression
  ihdr.writeUInt8(0, 11); // filter
  ihdr.writeUInt8(0, 12); // interlace

  const ihdrChunk = criarChunk("IHDR", ihdr);

  // Raw bitmap com filter byte (0) para cada scanline
  const scanlineLength = 1 + largura * 3;
  const rawData = Buffer.alloc(altura * scanlineLength);

  for (let y = 0; y < altura; y++) {
    const offset = y * scanlineLength;
    rawData[offset] = 0; // Filter None
    for (let x = 0; x < largura; x++) {
      const pixelOffset = offset + 1 + x * 3;
      // Desenha borda suave ou gradiente simples
      const distBorda = Math.min(x, y, largura - 1 - x, altura - 1 - y);
      if (distBorda < 1 && largura >= 16) {
        rawData[pixelOffset] = Math.max(0, r - 30);
        rawData[pixelOffset + 1] = Math.max(0, g - 30);
        rawData[pixelOffset + 2] = Math.max(0, b - 30);
      } else {
        rawData[pixelOffset] = r;
        rawData[pixelOffset + 1] = g;
        rawData[pixelOffset + 2] = b;
      }
    }
  }

  const compressedData = zlib.deflateSync(rawData);
  const idatChunk = criarChunk("IDAT", compressedData);

  // Chunk IEND
  const iendChunk = criarChunk("IEND", Buffer.alloc(0));

  return Buffer.concat([signature, ihdrChunk, idatChunk, iendChunk]);
}

function criarChunk(type, data) {
  const length = data.length;
  const chunk = Buffer.alloc(8 + length + 4);
  chunk.writeUInt32BE(length, 0);
  chunk.write(type, 4, 4, "ascii");
  data.copy(chunk, 8);

  const crcTarget = Buffer.concat([Buffer.from(type, "ascii"), data]);
  const crc = calcularCRC(crcTarget);
  chunk.writeUInt32BE(crc, 8 + length);
  return chunk;
}

// Tabela e calculo de CRC32 padrao PNG
let crcTable = null;
function calcularCRC(buf) {
  if (!crcTable) {
    crcTable = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) {
        if (c & 1) c = 0xedb88320 ^ (c >>> 1);
        else c = c >>> 1;
      }
      crcTable[n] = c;
    }
  }
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) {
    c = crcTable[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
}

const dirIcons = path.join(__dirname, "..", "icons");
if (!fs.existsSync(dirIcons)) fs.mkdirSync(dirIcons, { recursive: true });

// Cor: Azul/Indigo do SIGEduc Auto (#4F46E5 -> 79, 70, 229)
fs.writeFileSync(path.join(dirIcons, "icon16.png"), criarPNG(16, 16, 79, 70, 229));
fs.writeFileSync(path.join(dirIcons, "icon48.png"), criarPNG(48, 48, 79, 70, 229));
fs.writeFileSync(path.join(dirIcons, "icon128.png"), criarPNG(128, 128, 79, 70, 229));

console.log("✓ Ícones gerados em extensao-notas/icons/ (icon16.png, icon48.png, icon128.png)");
