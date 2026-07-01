# Schematron / ISO SVRL XSLT2 credits

This directory contains vendored Schematron support XSLT files used for ISO Schematron validation (including the optional XSLT2 / Saxon-based path).

Notable files:
- `iso_svrl_for_xslt2.xsl`
- `iso_schematron_skeleton_for_saxon.xsl`
- `iso_schematron_message_xslt2.xsl`

License/attribution:
- The vendored XSLT files include license headers with the original author/copyright attribution and an **MIT license** notice (some files also reference their historical availability under other permissive terms).
- Please keep these headers intact when updating/re-vendoring these assets.

Security note:
- The application intentionally does not download runtime Schematron assets.
- XSLT files in this directory should be treated as trusted, version-controlled dependencies.
