# Saxon-HE (XSLT2) setup for Schematron

This project uses Schematron rules that require XSLT2 features (XPath 2.0, regex functions, distinct-values, etc.). While `lxml` provides ISO Schematron for many cases, `lxml`'s implementation is limited to XSLT1 and cannot process rules that declare `queryBinding="xslt2"`.

To validate such Schematron rules on the server, we use Saxon-HE (a Java XSLT 2/3 processor) to compile Schematron to an XSLT validator and run validation producing SVRL output.

Quick setup (local):

1. Download Saxon via the helper script:

   ```bash
   ./tools/schematron/install_saxon.sh
   ```

   This places `saxon-he.jar` in `tools/saxon/` by default. You can override the version with `SAXON_VERSION`.

2. Set `SAXON_JAR` environment variable, e.g.: 

   ```bash
   export SAXON_JAR=$(pwd)/tools/saxon/saxon-he.jar
   ```

3. Run tests that require Saxon (integration tests):

   ```bash
   export SAXON_JAR=${SAXON_JAR}
   pytest tests/integration/test_schematron_saxon_integration.py -q
   ```

Notes:
- The Schematron validator will auto-download `iso_svrl_for_xslt2.xsl` if missing (from the canonical Schematron repo), unless `SCHEMATRON_ISO_XSL_URL` is set to an alternate URL.
- In CI, add a job to download Saxon and set `SAXON_JAR` to run these integration tests.
