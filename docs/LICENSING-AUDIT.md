# Licensing audit

This is a source audit, not legal advice.

| Surface | Evidence | Current interpretation | Action |
| --- | --- | --- | --- |
| Root repository | LICENSE | Proprietary, all rights reserved, with an OraOne Technologies Pvt. Ltd. copyright line and contact address | Confirm legal owner and contact before publishing or changing |
| Widget package | frontend/packages/oraone-widget/package.json | Declares MIT while the root repository is proprietary | Resolve whether the widget is intentionally separately licensed; do not silently relicense |
| Widget README | frontend/packages/oraone-widget/README.md | Repeats MIT attribution | Keep only after package license decision is approved |
| Dependencies | frontend/package-lock.json and backend/requirements.txt | Declared, but no generated SBOM or full license report in this checkout | Generate a dependency license/SBOM report before release |

No license files were rewritten. The widget repository URL now points to this checkout's actual GitHub repository; that does not settle ownership or distribution rights.
