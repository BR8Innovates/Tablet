#!/bin/bash
cd /tmp/claude-0/-home-user-Tablet/4e5f48e0-1baf-5a1d-9f0f-ce844ee516ee/scratchpad/uponly-build
export B=$PWD SPEC_CONTENT=dev_content12 DOC_TITLE="Afillar Insurance APIs" DOC_SUB="Developer Guide" DOC_TAG="Architecture, code, configuration, workflow, portal and operations: the hand-over reference for maintainers" DOC_VERSION="Version 1.2" DOC_PREP="Prepared for the Afillar Channel Integration Program" DOC_OUT="Afillar_API_Developer_Guide_v1.2" DOC_DATE="05-Oct-2026"
python3 render_spec.py && python3 render_docx.py
