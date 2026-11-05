// scripts/setup_python.mjs — utilitário multiplataforma (Windows/macOS/Linux).
// Cria o virtualenv e instala as dependências do backend + pipeline.
import { $ } from "zx";
import process from "node:process";

const __python = process.env.PYTHON ?? "python3";
console.log(`[setup] criando virtualenv (python=${__python})…`);
await $`${__python} -m venv .venv`;
const isWin = process.platform === "win32";
const pip = isWin ? `.venv\\Scripts\\pip` : ".venv/bin/pip";
await $`${pip} install -r backend/requirements.txt -r pipeline/requirements.txt`;
console.log("[setup] ok — ativar com: source .venv/bin/activate  (Windows: .venv\\Scripts\\activate)");
