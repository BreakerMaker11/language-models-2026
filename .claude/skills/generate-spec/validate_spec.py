"""
Validate a YAML implementation spec file.
Usage: python .claude/scripts/validate_spec.py <path_to_spec.yaml>
Outputs pass/fail JSON to stdout.
"""
import json
import sys
from pathlib import Path


REQUIRED_SECTIONS = [
    # Each entry is a list of accepted key names (any one must be present)
    ["approach"],
    ["tasks"],
    ["integration_steps", "integration steps"],
    ["evaluation_plan", "evaluation plan"],
    ["reference_materials", "reference materials"],
    ["verification"],
]


def load_yaml_keys(path: Path) -> list[str]:
    """
    Extract top-level keys from a YAML file without a full YAML parser dependency.
    Falls back to regex scanning for top-level keys (lines not indented, ending with ':').
    """
    try:
        import yaml  # type: ignore
        with open(path) as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            return list(data.keys())
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: scan for top-level keys via regex
    import re
    keys = []
    pattern = re.compile(r"^([A-Za-z_][A-Za-z0-9_ ]*):", re.MULTILINE)
    text = path.read_text()
    for match in pattern.finditer(text):
        key = match.group(1).strip()
        if key not in keys:
            keys.append(key)
    return keys


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"valid": False, "missing_sections": [], "warnings": ["No spec file path provided"]}))
        sys.exit(1)

    spec_path = Path(sys.argv[1])
    if not spec_path.exists():
        print(json.dumps({
            "valid": False,
            "missing_sections": ["<file not found>"],
            "warnings": [f"File not found: {spec_path}"]
        }))
        sys.exit(1)

    keys = [k.lower() for k in load_yaml_keys(spec_path)]

    missing = []
    for section_options in REQUIRED_SECTIONS:
        found = any(opt.lower() in keys for opt in section_options)
        if not found:
            missing.append(section_options[0])

    warnings = []
    # Check for success criteria
    if not any(k in keys for k in ["success_criteria", "success criteria"]):
        warnings.append("No success criteria defined")
    result = {
        "valid": len(missing) == 0,
        "missing_sections": missing,
        "warnings": warnings,
    }
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
