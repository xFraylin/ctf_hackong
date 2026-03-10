# ACME Hack ERP - Dockerfile
# Aplicación vulnerable para laboratorio CTF

FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de requisitos
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Crear directorios necesarios con permisos correctos
RUN mkdir -p uploads templates /tmp && chmod -R 777 /tmp

# Crear archivo de flag para LFI
RUN echo "flag{hackcon_lfi}" > /app/flag_lfi.txt && chmod 644 /app/flag_lfi.txt

# Crear documentos corporativos de ejemplo en uploads
RUN echo "ACME Corporation - Manual de Usuario\nGuía básica de uso del sistema ERP ACME.\nIncluye procedimientos generales para usuarios finales." > /app/uploads/manual_usuario.txt && \
    echo "ACME Corporation - Política de Seguridad de la Información\nEste documento describe las políticas internas de seguridad,\ncontroles de acceso y manejo de información sensible." > /app/uploads/politica_seguridad.txt && \
    echo "ACME Corporation - Contrato Estándar para Clientes\nTérminos y condiciones del servicio de plataforma ERP." > /app/uploads/contrato_cliente.txt && \
    echo "ACME Corporation - Procedimiento de Respaldo de Base de Datos\nFrecuencia de respaldos, almacenamiento y pruebas de restauración." > /app/uploads/procedimiento_backup.txt && \
    echo "ACME Corporation - Reporte Financiero Trimestral\nResumen ejecutivo de ingresos, gastos y proyecciones." > /app/uploads/reporte_financiero.txt

# Crear archivo de flag para command injection
RUN echo "flag{hackcon_command_injection}" > /app/flag_ssti.txt && chmod 644 /app/flag_ssti.txt

# Exponer puerto
EXPOSE 5000

# Variable de entorno para Flask
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

# Comando para ejecutar la aplicación
CMD ["python", "app.py"]
