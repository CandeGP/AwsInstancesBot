# AwsInstancesBot

> Bot de Discord para gestionar instancias de juego en AWS de forma automática, segura y escalable.

Permite crear, iniciar, detener y monitorear servidores directamente desde comandos en Discord. Está pensado para juegos como **Project Zomboid**, con foco en el control de costos y la seguridad de la infraestructura.

## Objetivo

Automatizar la administración de servidores de juego en AWS mediante un bot de Discord, integrando servicios como **Lambda**, **EC2**, **RDS/DynamoDB**, **CloudWatch** y **SNS**.

## Arquitectura

```text
Usuario en Discord
        |
        v
Bot de Discord -----> AWS Lambda -----> EC2: servidor de juego
        |                   |                    |
        v                   v                    v
Secrets Manager       IAM Roles        CloudWatch: métricas y logs
        |
        v
Notificaciones en Discord / SNS

RDS/DynamoDB: configuraciones y progreso
```

## Estructura del repositorio

```text
AwsInstancesBot/
├── src/                  # Código fuente del bot
├── infra/                # Terraform / CloudFormation
├── docker/               # Dockerfile y docker-compose.yml
├── scripts/              # Provisioning y userdata
├── docs/                 # Diagramas, documentación y runbooks
├── .github/workflows/    # CI/CD con GitHub Actions
├── .env.example          # Variables de entorno de ejemplo
└── README.md
```

## Requisitos

- Cuenta de AWS con Free Tier activa.
- AWS CLI configurado.
- Node.js 18+ o Python 3.10+.
- Docker para el entorno local.
- Token del bot de Discord guardado en AWS Secrets Manager.

## Instalación rápida

```bash
git clone https://github.com/CandeGP/AwsInstancesBot.git
cd AwsInstancesBot
cp .env.example .env
docker compose -f docker/docker-compose.yml up --build -d
```

El contenedor queda corriendo en segundo plano (`restart: unless-stopped`), por lo que el bot se mantiene activo sin tener que ejecutarlo manualmente en cada sesión. Para ver logs: `docker compose -f docker/docker-compose.yml logs -f`. Para detenerlo: `docker compose -f docker/docker-compose.yml down`.

> Nunca subas el archivo `.env` al repositorio. Usa AWS Secrets Manager para los secretos de producción.

## Servicios de AWS

| Servicio | Responsabilidad |
| --- | --- |
| **Lambda** | Ejecuta acciones sobre EC2 y la base de datos. |
| **EC2** | Aloja el servidor de juego. |
| **RDS / DynamoDB** | Guarda configuraciones y progreso. |
| **CloudWatch** | Monitorea rendimiento y costos. |
| **SNS** | Envía alertas y notificaciones. |
| **IAM** | Aplica permisos mínimos a cada componente. |
| **Secrets Manager** | Almacena tokens y claves de forma segura. |

## Comandos del bot

| Comando | Descripción |
| --- | --- |
| `/startserver` | Enciende la instancia EC2 del juego. Cualquier miembro del servidor de Discord. |
| `/stopserver` | Apaga la instancia EC2. Cualquier miembro del servidor de Discord. |
| `/status` | Muestra el estado del bot y del servidor (estado, tipo de instancia, IP y puerto). |
| `/notificaciones` | Elige el canal donde llegan los avisos del servidor. Solo administradores de Discord. |
| `/stats` | Reporta rendimiento y costos estimados. |
| `/upgrade` | Cambia el tipo de instancia, por ejemplo `t3.micro` a `t4.large`. |

### Conexión del bot con AWS

Flujo: **Discord → bot → API Gateway → Lambda (Python) → EC2**. Las rutas (`GET /server`, `POST /server/start`, `POST /server/stop` y `PUT /config/notifications`) requieren el header `x-api-key`. Tras el despliegue de Terraform, configura el bot con:

```bash
terraform -chdir=infra output -raw server_api_url   # SERVER_API_URL
terraform -chdir=infra output -raw server_api_key   # SERVER_API_KEY
```

Agrega ambos valores a `.env`. Los comandos `/startserver`, `/stopserver` y `/status` los puede usar cualquier miembro del servidor de Discord (no funcionan por mensaje directo); solo `/notificaciones` exige ser administrador.

### Notificaciones en Discord

Flujo: **EventBridge → Lambda `notifier` → webhook de Discord**. Avisa cuando el servidor se enciende (con la IP y el puerto), se apaga (indicando si fue por AutoStop o por `/stopserver`), se elimina la instancia, o falla la verificación de estado de EC2 (y cuando se recupera). Funciona sin importar quién cambió el estado: el bot, AutoStop o la consola de AWS.

Se configura **desde Discord**, sin tocar AWS ni GitHub: un administrador ejecuta `/notificaciones canal:#canal`. El bot crea un webhook en ese canal, lo guarda en AWS (SSM Parameter Store, SecureString, a través de `PUT /config/notifications`) y publica un mensaje de prueba. Para cambiar de canal basta con repetir el comando; el notifier detecta el cambio en un máximo de 5 minutos.

- Requiere que el bot tenga el permiso **Gestionar webhooks** en ese canal.
- La URL del webhook es un secreto: no se muestra, no se guarda en Terraform ni en GitHub, y la API nunca la devuelve.
- Al cambiar de canal, el webhook del canal anterior queda creado pero sin uso; puedes borrarlo en *Ajustes del canal → Integraciones*.
- Mientras no se ejecute `/notificaciones`, el notifier lo registra en los logs y no envía nada.

Alternativa manual (sin el bot):

```bash
aws ssm put-parameter --name /aws-instances-bot/discord-webhook-url \
  --type SecureString --value "https://discord.com/api/webhooks/..." --overwrite
```

Los tests de las Lambdas se ejecutan con `python -m unittest discover -s lambdas/tests -t lambdas -v`.

## Monitoreo y control de costos

| Herramienta | Uso |
| --- | --- |
| **CloudWatch Metrics** | Monitorea CPU, memoria y tráfico. |
| **AWS Budgets** | Envía alertas al 50 %, 80 % y 100 % del presupuesto. |
| **AutoStop Lambda** | Apaga instancias inactivas automáticamente. |
| **SNS** | Envía notificaciones de rendimiento y costos. |

##  CI/CD

El flujo de entrega utiliza las siguientes herramientas:

- **GitHub Actions**
        - `ci.yml`: build, lint y tests.
        - `cd.yml`: despliegue automático a AWS mediante ECR/Fargate.
- **Terraform**: infraestructura como código.
- **Docker**: empaquetado y despliegue local o en AWS Fargate.

##  Tests

- Pruebas unitarias para los comandos del bot.
- Pruebas de integración para funciones Lambda y conexión con AWS.
- Mocks de servicios AWS para pruebas locales.

##  Documentación adicional

- [`docs/architecture.md`](docs/architecture.md): diagramas y flujo de datos.
- [`docs/generalRoadmap.md`](docs/generalRoadmap.md): Vistazo de el flujo de trabajo que se presentara.
- [`docs/requirements.md`](docs/requirements.md): Requerimientos funcionales y no funcionales del proyecto.

## Contribuir
- Haz fork del repositorio.
- Crea una rama: feature/nueva-funcionalidad.
- Envía un pull request con descripción clara.