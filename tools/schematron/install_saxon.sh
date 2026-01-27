#!/usr/bin/env bash
set -euo pipefail

: ${SAXON_VERSION:=12.6}
: ${DEST:=tools/saxon}
: ${SAXON_JAR:=${DEST}/saxon-he.jar}

mkdir -p "$DEST"

# Try both capitalized and lowercase artifact names (Maven Central uses 'Saxon-HE' as the artifact directory)
URL1="https://repo1.maven.org/maven2/net/sf/saxon/Saxon-HE/${SAXON_VERSION}/Saxon-HE-${SAXON_VERSION}.jar"
URL2="https://repo1.maven.org/maven2/net/sf/saxon/Saxon-HE/${SAXON_VERSION}/saxon-he-${SAXON_VERSION}.jar"

echo "Downloading Saxon-HE ${SAXON_VERSION} from Maven Central..."
if curl -fSL "$URL1" -o "$SAXON_JAR"; then
  echo "Downloaded Saxon to $SAXON_JAR (from $URL1)"
  echo "Set environment variable SAXON_JAR=$SAXON_JAR to enable Schematron XSLT2 validation."
elif curl -fSL "$URL2" -o "$SAXON_JAR"; then
  echo "Downloaded Saxon to $SAXON_JAR (from $URL2)"
  echo "Set environment variable SAXON_JAR=$SAXON_JAR to enable Schematron XSLT2 validation."
else
  echo "Failed to download Saxon from $URL1 or $URL2" >&2
  exit 1
fi

# Also download xmlresolver (required by Saxon at runtime)
XMLRESOLVER_VER=${XMLRESOLVER_VER:-6.0.21}
XMLRESOLVER_JAR=${DEST}/xmlresolver-${XMLRESOLVER_VER}.jar
XMLRESOLVER_URL="https://repo1.maven.org/maven2/org/xmlresolver/xmlresolver/${XMLRESOLVER_VER}/xmlresolver-${XMLRESOLVER_VER}.jar"

if [ -f "$XMLRESOLVER_JAR" ]; then
  echo "xmlresolver already present: $XMLRESOLVER_JAR"
else
  echo "Downloading xmlresolver ${XMLRESOLVER_VER}..."
  if curl -fSL "$XMLRESOLVER_URL" -o "$XMLRESOLVER_JAR"; then
    echo "Downloaded xmlresolver to $XMLRESOLVER_JAR"
  else
    echo "Warning: failed to download xmlresolver from $XMLRESOLVER_URL" >&2
    echo "You may need to install xmlresolver manually if Saxon fails to run."
  fi
fi

echo "Done. To enable Schematron XSLT2 validation, set SAXON_JAR=${SAXON_JAR} and XMLRESOLVER_JAR=${XMLRESOLVER_JAR}"
