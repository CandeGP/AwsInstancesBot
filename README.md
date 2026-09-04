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
docker-compose up --build
```

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
| `/startserver` | Crea o inicia una instancia EC2 con el juego configurado. |
| `/stopserver` | Detiene la instancia y guarda el estado. |
| `/status` | Muestra el estado actual del servidor. |
| `/stats` | Reporta rendimiento y costos estimados. |
| `/upgrade` | Cambia el tipo de instancia, por ejemplo `t3.micro` a `t4.large`. |

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