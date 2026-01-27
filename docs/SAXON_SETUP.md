# Saxon-HE (XSLT2) setup for Schematron

This project uses Schematron rules that require XSLT2 features (XPath 2.0, regex functions, distinct-values, etc.). While `lxml` provides ISO Schematron for many cases, `lxml`'s implementation is limited to XSLT1 and cannot process rules that declare `queryBinding="xslt2"`.

To validate such Schematron rules on the server, we use Saxon-HE (a Java XSLT 2/3 processor) to compile Schematron to an XSLT validator and run validation producing SVRL output.

Quick setup (local):

1. Download Saxon via the helper script:

   ```bash
   ./tools/schematron/install_saxon.sh
   ```

   This places `saxon-he.jar` in `tools/saxon/` by default. You can override the version with `SAXON_VERSION`.

2. Set `SAXON_JAR` (and `XMLRESOLVER_JAR`) environment variables, e.g.: 

   ```bash
   export SAXON_JAR=$(pwd)/tools/saxon/saxon-he.jar
   export XMLRESOLVER_JAR=$(pwd)/tools/saxon/xmlresolver-6.0.21.jar
   ```

3. Ensure the ISO SVRL XSLT2 stylesheet is available and valid.
   - By default the validator will try to download `tools/schematron/iso_svrl_for_xslt2.xsl` from the canonical Schematron repo. If that download fails (404 or network blocked) you can provide a local copy or set:

   ```bash
   export SCHEMATRON_ISO_XSL_URL="https://your-mirror/iso_svrl_for_xslt2.xsl"
   ```

4. Run tests that require Saxon (integration tests):

   ```bash
   export SAXON_JAR=${SAXON_JAR}
   export XMLRESOLVER_JAR=${XMLRESOLVER_JAR}
   pytest tests/integration/test_schematron_saxon_integration.py -q
   ```

Notes:
- The integration tests will be skipped if `SAXON_JAR` is not configured or if the ISO SVRL XSLT2 stylesheet is not available/invalid; see the test output for skip reasons.
- In CI, add a job to download Saxon and `xmlresolver` and set `SAXON_JAR` and `XMLRESOLVER_JAR` to run these integration tests.
