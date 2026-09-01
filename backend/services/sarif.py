"""
Phase F : SARIF export for the ThirdEye council.

Converts a run_council() result dict (see services/council.py for the exact
schema) into a SARIF 2.1.0 JSON object — the standard "Static Analysis Results
Interchange Format" that GitHub code-scanning, VS Code SARIF viewers and most
security dashboards ingest natively. This is the integration seam between
ThirdEye and the rest of the world: one council run -> one SARIF "run".

SARIF concepts we map onto:
  - tool.driver.rules : one rule per distinct vulnerability *type* seen
                        (e.g. "reentrancy", "access_control"). The rule carries
                        the human description; results reference it by id.
  - results           : one per confirmed vulnerability. level is derived from
                        severity, the message is the description, evidence is
                        carried in relatedLocations + a property bag.
  - locations         : a physicalLocation pointing at source_path. The council
                        does not produce reliable line numbers (line is usually
                        None), so we point at the file and rely on the quoted
                        evidence to localize within it.

There is NO LLM call here — pure data transformation, so it is deterministic
and trivially testable. It is robust to an empty `vulnerabilities` list: a
clean (GO) run still produces a valid SARIF object with zero results.
"""

# Where a SARIF consumer can learn what produced these results.
ARGUS_INFO_URI = "https://github.com/third-eye-capstone/argus"
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
SARIF_VERSION = "2.1.0"

# severity (council vocabulary) -> SARIF result.level. SARIF only knows
# error/warning/note/none, so we collapse the four severities onto three.
_SEVERITY_TO_LEVEL = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
}


def _level_for_severity(severity: str) -> str:
    """Map a council severity onto a SARIF level, defaulting unknown/blank
    severities to 'warning' (visible but not failing) rather than dropping them."""
    return _SEVERITY_TO_LEVEL.get((severity or "").lower(), "warning")


def _rule_for_type(vuln_type: str) -> dict:
    """Build a SARIF reportingDescriptor (a 'rule') for one vulnerability type.
    id is the type itself so results can reference it by ruleId."""
    title = (vuln_type or "unknown").replace("_", " ").title()
    return {
        "id": vuln_type or "unknown",
        "name": "".join(part.capitalize() for part in (vuln_type or "unknown").split("_")),
        "shortDescription": {"text": f"{title} vulnerability"},
        "fullDescription": {
            "text": f"A {title} class finding raised by an ThirdEye council specialist."
        },
        # helpUri lets a viewer deep-link to docs for this rule class.
        "helpUri": f"{ARGUS_INFO_URI}#{vuln_type or 'unknown'}",
    }


def _result_for_vuln(vuln: dict, source_path: str) -> dict:
    """Build one SARIF result object from one council vulnerability dict."""
    vuln_type = vuln.get("type", "unknown")
    severity = vuln.get("severity", "")
    description = vuln.get("description", "") or f"{vuln_type} finding"
    evidence = vuln.get("evidence_quote", "") or ""
    source = vuln.get("source", "") or f"council:{vuln_type}"
    line = vuln.get("line")

    # physicalLocation: always point at the file. If the council ever supplies a
    # concrete line we attach a region so viewers can jump straight to it.
    physical_location: dict = {"artifactLocation": {"uri": source_path}}
    if isinstance(line, int) and line > 0:
        physical_location["region"] = {"startLine": line}

    result: dict = {
        "ruleId": vuln_type or "unknown",
        "level": _level_for_severity(severity),
        "message": {
            # The description is the primary message; we append the verbatim
            # evidence quote so it survives in any viewer that only shows text.
            "text": description + (f"\n\nEvidence: {evidence}" if evidence else "")
        },
        "locations": [{"physicalLocation": physical_location}],
        # partialFingerprints make a finding stable across runs / file moves so
        # GitHub can dedupe and track it — keyed on the source specialist + type.
        "partialFingerprints": {
            "argus/source-type": f"{source}:{vuln_type}",
        },
        # Property bag: ThirdEye-specific metadata SARIF has no first-class slot for.
        "properties": {
            "confidence": vuln.get("confidence"),
            "severity": severity,
            "model": vuln.get("model"),
            "provider": vuln.get("provider"),
            "dynamic_status": vuln.get("dynamic_status"),
            "source": source,
            "proposed_property": vuln.get("proposed_property", ""),
        },
    }

    # relatedLocations carries the evidence quote anchored to the file, giving
    # SARIF viewers a second clickable location with the exact offending code.
    if evidence:
        result["relatedLocations"] = [
            {
                "physicalLocation": {"artifactLocation": {"uri": source_path}},
                "message": {"text": f"Evidence quote:\n{evidence}"},
            }
        ]

    return result


def to_sarif(result: dict, source_path: str = "contract.sol") -> dict:
    """Convert a council result dict into a SARIF 2.1.0 JSON object.

    One rule per distinct vulnerability type encountered; one result per
    vulnerability. Safe on an empty vulnerabilities list (valid clean run).

    Args:
        result: the dict returned by services.council.run_council().
        source_path: the artifact URI used for every result location
                     (the scanned .sol path, relative to the repo root).

    Returns:
        a dict that is a valid SARIF 2.1.0 log, JSON-serializable as-is.
    """
    vulnerabilities = result.get("vulnerabilities", []) or []

    # Deduplicate rules by type, preserving first-seen order for stable output.
    rules: list[dict] = []
    seen_types: set[str] = set()
    for vuln in vulnerabilities:
        vuln_type = vuln.get("type", "unknown") or "unknown"
        if vuln_type not in seen_types:
            seen_types.add(vuln_type)
            rules.append(_rule_for_type(vuln_type))

    results = [_result_for_vuln(vuln, source_path) for vuln in vulnerabilities]

    # Carry the council's top-level verdict/stats onto the run's property bag so
    # downstream consumers can read the GO/NO-GO gate without re-deriving it.
    run_properties = {
        "final_verdict": result.get("final_verdict"),
        "mode": result.get("mode"),
        "contract_name": result.get("contract_name"),
        "summary": result.get("summary"),
        "raven_note": result.get("raven_note"),
        "stats": result.get("stats", {}),
    }

    return {
        "version": SARIF_VERSION,
        "$schema": SARIF_SCHEMA,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ThirdEye",
                        "informationUri": ARGUS_INFO_URI,
                        "rules": rules,
                    }
                },
                "results": results,
                "properties": run_properties,
            }
        ],
    }
