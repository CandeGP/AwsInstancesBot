// Arma una carpeta autocontenida en release/ con solo lo necesario para correr el bot
// (sin src/ ni dependencias de desarrollo), lista para copiarse a otra maquina (p. ej. un NAS)
// y levantarse ahi con Docker sin construir desde el codigo fuente.
// Uso: npm run release  (ejecuta `npm run build` antes automaticamente)
import { cpSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), '..');
const distDir = join(repoRoot, 'dist');
const releaseDir = join(repoRoot, 'release');

if (!existsSync(distDir)) {
  console.error('No existe dist/. Corre "npm run build" antes (este script ya lo hace via "npm run release").');
  process.exit(1);
}

rmSync(releaseDir, { recursive: true, force: true });
mkdirSync(join(releaseDir, 'docker'), { recursive: true });

cpSync(distDir, join(releaseDir, 'dist'), { recursive: true });
cpSync(join(repoRoot, 'package.json'), join(releaseDir, 'package.json'));
cpSync(join(repoRoot, 'package-lock.json'), join(releaseDir, 'package-lock.json'));
cpSync(join(repoRoot, 'docker', 'Dockerfile.dist'), join(releaseDir, 'docker', 'Dockerfile'));
cpSync(join(repoRoot, 'docker', 'docker-compose.yml'), join(releaseDir, 'docker', 'docker-compose.yml'));

console.log(`Listo: ${releaseDir}`);
console.log('Contenido: dist/, package.json, package-lock.json, docker/Dockerfile, docker/docker-compose.yml');
console.log('');
console.log('Siguiente paso: copia esa carpeta a la otra maquina (ej. con scp o rsync), agrega');
console.log('ahi un archivo .env (DISCORD_TOKEN, SERVER_API_URL, SERVER_API_KEY) junto a package.json,');
console.log('y corre: docker compose -f docker/docker-compose.yml up --build -d');
