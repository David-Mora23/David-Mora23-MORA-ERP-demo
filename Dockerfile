# Usa una imagen oficial de Python como base
FROM python:3.11-slim

# Evita que Python escriba archivos .pyc en el disco
ENV PYTHONDONTWRITEBYTECODE=1
# Evita que Python amortigüe stdout y stderr (útil para logs)
ENV PYTHONUNBUFFERED=1

# Establece el directorio de trabajo
WORKDIR /app

# Copia los requerimientos del backend e instala dependencias
COPY easyerp/backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copia el código completo de la aplicación (backend y frontend)
COPY easyerp/ /app/easyerp/

# Expone el puerto por defecto de Cloud Run (8080)
EXPOSE 8080

# Comando para ejecutar la aplicación con Gunicorn en el puerto dinámico asignado por Cloud Run
CMD ["sh", "-c", "gunicorn --chdir easyerp/backend --bind 0.0.0.0:${PORT:-8080} app:app"]
