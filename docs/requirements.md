# AWSInstancesBot

Documento de requisitos para un bot de Discord capaz de gestionar servidores de juego en AWS.

## Requisitos funcionales

### Gestión de instancias

- Crear instancias EC2 dinámicamente desde Discord.
- Permitir configurar el tipo de instancia, la región, el juego y el almacenamiento.
- Reutilizar una única base de datos para guardar configuraciones y estados de juego. La solución podrá utilizar DynamoDB o RDS.
- Instalar el juego automáticamente. Inicialmente se utilizará Project Zomboid mediante scripts de `userData` o una imagen AMI personalizada.
- Apagar automáticamente la instancia cuando no haya jugadores activos, utilizando Lambda y eventos de CloudWatch.
- Cambiar el tipo de instancia mediante el comando `/upgrade`.

### Integración con Discord

| Comando | Propósito |
| --- | --- |
| `/startserver` | Crear o iniciar el servidor de juego. |
| `/stopserver` | Detener el servidor y conservar su estado. |
| `/status` | Consultar el estado actual de la instancia. |
| `/stats` | Consultar métricas y costos estimados. |
| `/upgrade` | Cambiar a un tipo de instancia con mayor o menor capacidad |

El bot también debe generar logs y notificaciones cuando el servidor:

- Comience a arrancar.
- Cambie su configuración.
- Presente un error.

### Monitoreo y métricas

- El comando `/stats` debe mostrar, como mínimo, el consumo de CPU, memoria, tráfico y costo estimado.
- CloudWatch y SNS deben generar alertas automáticas cuando el costo o el rendimiento superen los límites definidos.

## Infraestructura y despliegue

- Desplegar el bot de Discord dentro de un contenedor Docker.
- Centralizar los logs en CloudWatch.
- Gestionar la infraestructura como código mediante Terraform o CloudFormation.

### Alternativas de ejecución

| Alternativa | Consideración |
| --- | --- |
| **AWS Fargate** | Opción serverless que reduce el mantenimiento de servidores. |
| **EC2 + Docker Compose** | Ofrece mayor control, pero requiere mantenimiento manual. |
| **ECS + ECR** | Recomendada si el proyecto crece y necesita ejecutar más de un bot. |

## Requisitos no funcionales

### Seguridad

- Almacenar tokens y claves en AWS Secrets Manager para evitar filtraciones de credenciales.
- Aplicar permisos mínimos mediante roles de IAM.

### Escalabilidad

- Evaluar el autoescalado cuando se alcance un número determinado de jugadores.
- Permitir aumentar la capacidad de la instancia según la demanda.

### Presupuesto

- Definir si el despliegue debe mantenerse dentro de AWS Free Tier.
- Establecer un presupuesto máximo y alertas de consumo.

## Decisiones pendientes

- Elegir entre DynamoDB y RDS.
- Elegir entre `userData` y una AMI personalizada para instalar Project Zomboid.
- Seleccionar la plataforma de ejecución principal: Fargate, EC2 + Docker Compose o ECS + ECR.
- Elegir Terraform o CloudFormation para la infraestructura como código.