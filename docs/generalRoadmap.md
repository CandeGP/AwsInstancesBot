# Arquitectura para Hosting de Juegos en AWS

**Autores:** Manuel Candelario y Moisés Morua  
**Duración estimada:** 10 semanas

## 🎯 Objetivo general

Hacer accesible el hosting de servidores de juegos, facilitando a los usuarios la creación y administración de instancias mediante una interfaz web y un bot de Discord.

## 🚫 Fuera de alcance

- Gestión de versiones del juego.
- Gestión de personalizaciones avanzadas.
- Soporte para múltiples regiones.
- Gestión de costos o facturación avanzada.

## ⚙️ Funciones objetivo

- Crear, iniciar, detener y eliminar instancias de servidores.
- Detectar cuando no hay jugadores y ejecutar un **AutoStop** con período de espera (*cooldown*).
- Modificar el tipo de instancia según la demanda.
- Registrar logs de arranque, finalización y errores.
- Monitorear rendimiento y costos.
- Gestionar permisos por usuario.
- Integrar servicios externos como Discord y Steam.

## 🧭 Roadmap del proyecto

### Fase 1: Diseño y planificación

**Semanas 1–2**

- Definir requisitos funcionales y no funcionales.
- Seleccionar los servicios AWS principales: EC2, Lambda, S3, CloudWatch, IAM, SNS y DynamoDB.
- Diseñar la arquitectura base, incluyendo red, flujo de datos y roles.
- Crear el repositorio en GitHub y la documentación inicial.

**Entregable:** requisitos aprobados, arquitectura documentada y repositorio inicial.

### Fase 2: Infraestructura y automatización

**Semanas 3–4**

- Implementar infraestructura como código con Terraform o CloudFormation.
- Configurar VPC, subredes, grupos de seguridad y roles IAM.
- Crear scripts para desplegar instancias automáticamente.
- Implementar AutoStop y AutoStart con Lambda y eventos de CloudWatch.

**Entregable:** infraestructura reproducible y ciclo básico de encendido/apagado automatizado.

### Fase 3: Integración del bot y backend

**Semanas 5–6**

- Implementar el bot de Discord con Node.js o Python.
- Conectar el bot con AWS SDK para crear, apagar y escalar instancias.
- Implementar autenticación y permisos por usuario o rol.
- Configurar logs y notificaciones mediante SNS o Discord Webhooks.
- Implementar el cooldown inteligente para apagar el servidor cuando no haya jugadores activos.

**Entregable:** bot funcional con comandos, permisos, notificaciones y control de EC2.

### Fase 4: Panel de control y monitoreo

**Semanas 7–8**

- Crear un dashboard web con React, API Gateway y Lambda.
- Integrar métricas de CloudWatch y alertas de facturación.
- Generar reportes automáticos de actividad y rendimiento.

**Entregable:** panel de monitoreo con métricas y reportes básicos.

### Fase 5: Optimización y escalabilidad

**Semanas 9–10**

- Implementar autoescalado dinámico según el número de jugadores.
- Evaluar balanceo de carga con ELB.
- Optimizar costos mediante Spot Instances.
- Preparar una demo funcional y documentada.

**Entregable:** demo estable, documentada y preparada para futuras mejoras.

## 🤖 Implementación del bot

### Configuración inicial

1. Registrar el bot en el [Discord Developer Portal](https://discord.com/developers/applications).
2. Generar el token y almacenarlo en AWS Secrets Manager.
3. Elegir una librería: `discord.py` para Python o `discord.js` para Node.js.

### Comandos y permisos

- Implementar `/startserver`, `/stopserver` y `/status` como comandos iniciales.
- Restringir los comandos sensibles a administradores o usuarios autorizados.
- Añadir comandos para consultar métricas y cambiar el tipo de instancia.

### Integración con AWS SDK

- Conectar el bot con AWS SDK para ejecutar acciones sobre EC2.
- Implementar operaciones equivalentes a `start_instances()` y `stop_instances()`.
- Enviar mensajes automáticos a Discord cuando una instancia se inicie, se detenga o falle.

### Logs y monitoreo

- Centralizar logs y métricas en CloudWatch.
- Usar SNS o CloudWatch para generar alertas automáticas.
- Notificar en Discord los cambios importantes del servidor.

## 💡 Ideas adicionales

- Backups automáticos de servidores y configuraciones.
- Integración con Discord OAuth2 para inicio de sesión y permisos.
- Sistema de créditos o tokens para usuarios.
- API pública para desarrolladores externos.
- Modo sandbox para pruebas sin costo real.
- Machine Learning para predecir patrones de uso y optimizar el encendido y apagado de instancias.

