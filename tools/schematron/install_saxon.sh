#!/usr/bin/env bash
set -euo pipefail

: ${SAXON_VERSION:=12.6}
: ${DEST:=tools/saxon}
: ${SAXON_JAR:=${DEST}/saxon-he.jar}

mkdir -p "$DEST"

URL="https://repo1.maven.org/maven2/net/sf/saxon/Saxon-HE/${SAXON_VERSION}/saxon-he-${SAXON_VERSION}.jar"

echo "Downloading Saxon-HE ${SAXON_VERSION} from Maven Central..."
if curl -fSL "$URL" -o "$SAXON_JAR"; then
  echo "Downloaded Saxon to $SAXON_JAR"
  echo "Set environment variable SAXON_JAR=$SAXON_JAR to enable Schematron XSLT2 validation."
else
  echo "Failed to download Saxon from $URL" >&2
  exit 1
fi
