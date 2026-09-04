# Diagramas de arquitectura

Este documento describe el flujo principal del sistema, la comunicación entre sus servicios y la organización de sus componentes.

## Diagrama de flujo

```mermaid
flowchart TD
	user([Usuario en Discord]) --> bot[Bot de Discord]
	bot --> command{Comando válido?}
	command -- No --> error[Respuesta de error]
	command -- Sí --> lambda[AWS Lambda]
	lambda --> ec2[Servidor de juego en EC2]
	ec2 --> database[(RDS / DynamoDB)]
	ec2 --> metrics[CloudWatch]
	metrics --> alerts{Supera un límite?}
	alerts -- Sí --> sns[SNS]
	alerts -- No --> response[Respuesta de estado]
	sns --> notification[Notificación en Discord]
	ec2 --> response
	response --> user
	error --> user
```

## Diagrama de secuencia

```mermaid
sequenceDiagram
	actor Usuario
	participant Bot as Bot de Discord
	participant Lambda as AWS Lambda
	participant EC2 as Servidor EC2
	participant BD as RDS / DynamoDB
	participant CW as CloudWatch
	participant SNS as SNS / Discord

	Usuario->>Bot: Envía un comando
	Bot->>Lambda: Procesa la solicitud
	Lambda->>EC2: Inicia, detiene o configura el servidor
	EC2->>BD: Consulta o actualiza el estado
	EC2-->>Lambda: Devuelve el resultado
	Lambda-->>Bot: Devuelve el estado de la operación
	Bot-->>Usuario: Confirma la operación
	EC2->>CW: Registra métricas y logs
	CW->>SNS: Envía una alerta si supera los límites
	SNS-->>Bot: Publica una notificación
```

## Diagrama de componentes

```mermaid
flowchart LR
	subgraph Discord[Integración con Discord]
		commands[Comandos Discord]
		oauth[Autenticación OAuth2]
		api[Integración con API de AWS]
		commands --> oauth
		oauth --> api
	end

	subgraph Control[Control de AWS]
		lambda[Funciones Lambda]
		ec2manager[Gestor de EC2]
		iam[Roles IAM]
		lambda --> ec2manager
		iam -. permisos .-> lambda
		iam -. permisos .-> ec2manager
	end

	subgraph Persistence[Persistencia y secretos]
		database[(RDS / DynamoDB)]
		secrets[Secrets Manager]
	end

	subgraph Monitoring[Monitoreo y alertas]
		cloudwatch[CloudWatch: logs y métricas]
		sns[SNS / Discord]
		cloudwatch --> sns
	end

	api --> lambda
	ec2manager --> database
	ec2manager --> secrets
	ec2manager --> cloudwatch
```

## Responsabilidades principales

| Componente | Responsabilidad |
| --- | --- |
| **Bot de Discord** | Recibe comandos, valida solicitudes y comunica resultados. |
| **AWS Lambda** | Ejecuta la lógica de control sin administrar servidores. |
| **EC2** | Aloja y ejecuta el servidor de juego. |
| **RDS / DynamoDB** | Conserva configuraciones y estados del juego. |
| **CloudWatch** | Centraliza logs, métricas y monitoreo. |
| **SNS** | Distribuye alertas y notificaciones. |
| **IAM** | Controla los permisos entre servicios. |
| **Secrets Manager** | Protege tokens, claves y otros secretos. |