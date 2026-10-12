/**
 * Script de empacotamento da extensão SIGEduc Auto para distribuição (.zip).
 * Cria um pacote limpo em 'dist/' contendo apenas os arquivos necessários de produção.
 *
 * Execução:
 *   node extensao-notas/scripts/empacotar.js
 */

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const raizExtensao = path.resolve(__dirname, "..");
const raizProjeto = path.resolve(raizExtensao, "..");
const dirDist = path.resolve(raizProjeto, "dist");
const manifestPath = path.resolve(raizExtensao, "manifest.json");

if (!fs.existsSync(manifestPath)) {
  console.error("❌ Erro: manifest.json não encontrado em", manifestPath);
  process.exit(1);
}

const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
const versao = manifest.version || "1.0.0";
console.log(`📦 Empacotando SIGEduc Auto v${versao}...`);

if (!fs.existsSync(dirDist)) {
  fs.mkdirSync(dirDist, { recursive: true });
}

// Cria diretório temporário para isolar os arquivos de produção
const dirTemp = path.resolve(dirDist, "temp_pacote");
if (fs.existsSync(dirTemp)) {
  fs.rmSync(dirTemp, { recursive: true, force: true });
}
fs.mkdirSync(dirTemp, { recursive: true });

// Lista de arquivos e pastas essenciais para o pacote de distribuição
const itensParaCopiar = [
  "manifest.json",
  "instalar_extensao.bat",
  "README.md",
  "icons",
  "content",
  "lib",
  "popup",
  "vendor"
];

for (const item of itensParaCopiar) {
  const origem = path.resolve(raizExtensao, item);
  const destino = path.resolve(dirTemp, item);
  if (fs.existsSync(origem)) {
    const stat = fs.statSync(origem);
    if (stat.isDirectory()) {
      copiarDiretorioRecursivo(origem, destino);
    } else {
      fs.copyFileSync(origem, destino);
    }
  }
}

function copiarDiretorioRecursivo(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  const entries = fs.readdirSync(src, { withFileTypes: true });
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copiarDiretorioRecursivo(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

const nomeZipVersao = `sigeduc-extensao-v${versao}.zip`;
const nomeZipLatest = `sigeduc-extensao.zip`;
const zipVersaoPath = path.resolve(dirDist, nomeZipVersao);
const zipLatestPath = path.resolve(dirDist, nomeZipLatest);

if (fs.existsSync(zipVersaoPath)) fs.unlinkSync(zipVersaoPath);
if (fs.existsSync(zipLatestPath)) fs.unlinkSync(zipLatestPath);

console.log("🗜️  Compactando arquivos em arquivo .zip...");

try {
  // Tenta tar (nativo em Windows 10/11, macOS e Linux)
  execSync(`tar -a -c -f "${zipVersaoPath}" -C "${dirTemp}" .`, { stdio: "pipe" });
} catch (eTar) {
  try {
    // Fallback para PowerShell Compress-Archive no Windows
    const cmdPs = `powershell -NoProfile -Command "Compress-Archive -Path '${dirTemp}\\*' -DestinationPath '${zipVersaoPath}' -Force"`;
    execSync(cmdPs, { stdio: "pipe" });
  } catch (ePs) {
    console.error("❌ Falha ao compactar arquivo:", ePs.message);
    process.exit(1);
  }
}

// Cria também a cópia padrão sem sufixo para links fixos de download
fs.copyFileSync(zipVersaoPath, zipLatestPath);

// Limpeza da pasta temporária
fs.rmSync(dirTemp, { recursive: true, force: true });

const tamanhoKb = (fs.statSync(zipVersaoPath).size / 1024).toFixed(1);
console.log(`\n🎉 Pacotes gerados com sucesso em ${dirDist}:`);
console.log(`   - ${nomeZipVersao} (${tamanhoKb} KB)`);
console.log(`   - ${nomeZipLatest} (${tamanhoKb} KB)`);
