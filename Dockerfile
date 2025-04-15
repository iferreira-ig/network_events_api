# Usar uma imagem base do Python
FROM python:3.11-slim

# Definir o diretório de trabalho
WORKDIR /app

# Copiar os arquivos de requisitos
COPY requirements.txt .

# Instalar as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY app.py .
COPY templates/ templates/

# Expor a porta 8080
EXPOSE 8080

# Definir o comando para iniciar a aplicação
CMD ["python", "app.py"]