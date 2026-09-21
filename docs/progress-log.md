# Registro de progreso

## 2026-09-18 — Dockerizar el bot para ejecución persistente

**Contexto:** el bot solo se ejecutaba con `npm run dev`/`npm start` en una terminal local, por lo que había que volver a levantarlo manualmente en cada sesión de trabajo para poder probar comandos.

**Estado anterior:** `docker/` existía como carpeta vacía; el README documentaba `docker-compose up --build` pero no había `Dockerfile` ni `docker-compose.yml` reales.

**Estado nuevo:**
- `docker/Dockerfile`: imagen `node:20-alpine`, instala dependencias con `npm ci`, compila con `npm run build` y arranca con `npm start` (CommandKit).
- `docker/docker-compose.yml`: servicio `bot` con `context: ..`, `env_file: ../.env` y `restart: unless-stopped` para que el contenedor se mantenga activo sin intervención manual.
- `.dockerignore`: excluye `node_modules/`, `dist/`, `.git/`, `.env`, `infra/`, `cdk.out/`, `docs/`, `.claude/` del contexto de build.
- `README.md`: instrucción de instalación actualizada a `docker compose -f docker/docker-compose.yml up --build -d`, con notas de `logs -f` y `down`.

**Archivos modificados:** `docker/Dockerfile` (nuevo), `docker/docker-compose.yml` (nuevo), `.dockerignore` (nuevo), `README.md`.

**Validación:** no se pudo ejecutar `docker build`/`docker compose up` porque esta máquina no tiene Docker instalado (`docker: command not found`). Sí se validó localmente que `npm run build` y `npm start` funcionan fuera de contenedor (el bot carga `.env`, registra el comando `/status` y refresca los comandos de aplicación en Discord), por lo que el mismo flujo dentro del `Dockerfile` debería comportarse igual. Pendiente: correr `docker compose -f docker/docker-compose.yml up --build` en una máquina con Docker antes de considerar esto validado end-to-end.

**Riesgos y decisiones pendientes:**
- No se agregó `HEALTHCHECK` ni límites de recursos al contenedor; evaluar si se necesita para producción.
- El contenedor no expone puertos (el bot no los necesita), pero si se agrega un panel de salud/monitoreo (Fase 4) habrá que revisar el compose.
- Sigue pendiente el resto de la Fase 2 (AutoStart) y la Fase 3 (conectar el bot con AWS SDK para `/startserver`, `/stopserver`, `/upgrade`), no relacionado con este cambio.

**Próximo criterio de aceptación:** ejecutar `docker compose -f docker/docker-compose.yml up --build -d` en una máquina con Docker Desktop/Engine y confirmar en los logs que el bot se conecta a Discord y responde `/status`.

## 2026-09-21 — Nombre del proyecto Docker y validación del despliegue

**Contexto:** tras desplegar el bot en Docker Desktop, el grupo aparecía como `docker` porque Compose toma por defecto el nombre de la carpeta del `docker-compose.yml`.

**Estado anterior:** proyecto `docker`, contenedor `docker-bot-1`.

**Estado nuevo:** `docker/docker-compose.yml` define `name: aws-instances-bot`, `container_name: aws-instances-bot` e `image: aws-instances-bot:latest`. El servicio sigue llamándose `bot`, así que los comandos del README no cambian.

**Archivos modificados:** `docker/docker-compose.yml`.

**Validación:** `docker ps` muestra el contenedor `aws-instances-bot` en estado `Up`; `docker compose ls` lista el proyecto `aws-instances-bot`; los logs muestran "Loaded 1 commands", "Refreshed 1 global application (/) commands" y `[status] Command executed successfully`. Con esto queda cumplido el criterio de aceptación de la entrada del 2026-09-18 (Docker validado end-to-end para `/status`).

**Riesgos y decisiones pendientes:**
- Cambiar `name:` crea un proyecto nuevo; el contenedor `docker-bot-1` anterior debe eliminarse con `down` si aún existe.
- Warning `MODULE_TYPELESS_PACKAGE_JSON` en los logs: cosmético, se resuelve con `"type": "module"` en `package.json` (no aplicado, requiere comprobar que el build sigue funcionando).

## 2026-09-21 — Cierre de la Fase 2: decisiones y protección de la instancia

**Contexto:** revisión del roadmap contra el repositorio. Se tomaron decisiones para dar por cerrada la Fase 2 y pasar a la Fase 3.

**Decisiones:**
- **AutoStart: descartado.** La instancia no debe encenderse sola. Solo se enciende con una acción explícita (futuro `/startserver`).
- **VPC:** se mantiene la VPC por defecto.
- **AutoStop:** se deja como está (por CPU, `auto_stop_enabled = true`). Probado manualmente por la autora; es una aproximación temporal, no detecta jugadores.
- **Tipo de instancia:** el servidor ya arranca. Subir a una instancia mayor queda para el futuro.
- **Documentación:** se deja como está por ahora, aunque `terraform-ec2-setup.md` difiere de `variables.tf` (`t3.medium`/`false`/40 GB en la doc contra `t3.micro`/`true`/20 GB en el código).

**Problema detectado:** `deploy-infra.yml` hace `terraform apply` en cada push a `main`. Terraform no recrea la instancia si ya existe (el estado está en S3), pero había dos riesgos: `data.aws_ami.ubuntu` usa `most_recent`, así que una AMI nueva de Canonical cambiaría `ami` y reemplazaría la instancia (con `delete_on_termination = true`, se perdería el mundo); y un cambio en `user_data` detiene y arranca la instancia sin volver a ejecutar el bootstrap. Además, el workflow corría con cambios de código del bot o de documentación que no afectan a la infraestructura.

**Estado nuevo:**
- `infra/main.tf`: `lifecycle { ignore_changes = [ami, user_data] }` en `aws_instance.game_server`.
- `.github/workflows/deploy-infra.yml`: el push solo dispara el despliegue si cambian `infra/**` (sin `infra/CDK/**`), `lambdas/**`, `scripts/ec2-user-data.sh` o el propio workflow; `workflow_dispatch` sigue disponible; `concurrency` evita dos despliegues a la vez.

**Archivos modificados:** `infra/main.tf`, `.github/workflows/deploy-infra.yml`, `docs/progress-log.md`.

**Validación:** `terraform fmt -check` y `terraform validate` pasan. No se ejecutó `terraform plan` (requiere backend S3 y credenciales); el primer despliegue tras el push debería mostrar cero cambios sobre la instancia. El YAML del workflow no se validó con un parser local.

**Riesgos y decisiones pendientes:**
- Con `ignore_changes` sobre `ami`, para cambiar de AMI o reinstalar hay que reemplazar la instancia a propósito (`terraform apply -replace=aws_instance.game_server`), asumiendo pérdida de datos si no hay backup.
- Cuando exista `/upgrade`, cambiar el tipo de instancia fuera de Terraform generará drift; habrá que decidir si Terraform lo ignora (`ignore_changes` en `instance_type`) o si sigue siendo la fuente de verdad.
- `apply -auto-approve` sigue activo por decisión explícita; no hay backups del mundo del juego.

**Próximo criterio de aceptación:** Fase 3, empezando por el endpoint de solo lectura `GET /status` (ver diseño acordado en la conversación: Discord bot → API Gateway → Lambda Python → EC2).
