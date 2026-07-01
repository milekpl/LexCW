FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Saxon for Schematron XSLT2 validation
COPY tools/schematron/install_saxon.sh /tmp/install_saxon.sh
RUN bash /tmp/install_saxon.sh && rm /tmp/install_saxon.sh

ENV SAXON_JAR=tools/saxon/saxon-he.jar
ENV XMLRESOLVER_JAR=tools/saxon/xmlresolver-6.0.21.jar

EXPOSE 5000

CMD ["python", "run.py"]
