"""Pure command planning. This module deliberately has no execution capability."""
from .common import AdapterError, canonical, checked_path, sha256

AUTH_MODES = {"subscription", "provider_api", "unknown"}


def plan(provider, workspace, model, cli_version, prompt, *, auth_mode="unknown", sandbox="read-only"):
    if provider not in {"codex", "claude"}:
        raise AdapterError("provider must be codex or claude")
    for value, label in [(model, "model"), (cli_version, "cli_version")]:
        if not isinstance(value, str) or not value.strip() or value.startswith("-") or any(ord(c) < 32 for c in value):
            raise AdapterError("explicit non-option " + label + " required")
    if not isinstance(prompt, str) or not prompt.strip():
        raise AdapterError("nonempty UTF-8 prompt required")
    if len(prompt.encode("utf-8")) > 1024 * 1024:
        raise AdapterError("prompt exceeds 1 MiB")
    if auth_mode not in AUTH_MODES:
        raise AdapterError("unsupported auth_mode; never supply credentials")
    if sandbox not in {"read-only", "workspace-write"}:
        raise AdapterError("unsupported sandbox")
    workspace = checked_path(workspace)
    if not workspace.is_dir():
        raise AdapterError("workspace must be a separately prepared existing directory")
    if provider == "codex":
        argv = ["codex", "-a", "never", "exec", "--json", "--ephemeral", "--sandbox", sandbox,
                "--cd", str(workspace), "--model", model, "-"]
        profile = "codex-exec-json-v1"
        verified = "local help 0.164.0; official exec event source (2026-10-27)"
    else:
        if sandbox != "read-only":
            raise AdapterError("sandbox is a Codex option; Claude sandbox cannot be asserted by this planner")
        argv = ["claude", "-p", "--input-format", "text", "--output-format", "stream-json", "--verbose",
                "--no-session-persistence", "--permission-mode", "dontAsk", "--model", model]
        profile = "claude-print-stream-json-v1"
        verified = "official documentation only (2026-10-27); Claude not installed/tested"
    result = {
        "schema_version": 1, "run_kind": "command_plan", "execution_status": "not_run",
        "business_status": "not_evaluated", "provider": provider, "model": model,
        "cli_version": cli_version, "cli_version_provenance": "caller_declared_not_probed",
        "auth_mode": auth_mode, "profile": profile, "contract_evidence": verified,
        "argv": argv, "cwd": str(workspace), "stdin": {"transport": "UTF-8 bytes on stdin", "sha256": sha256(prompt.encode("utf-8")), "bytes": len(prompt.encode("utf-8"))},
        "prompt_stored": False, "shell": False, "launch_supported": False,
        "resume": False, "real_integration_tested": False,
        "operator_preflight": {"independent_workspace_provenance": "required_not_verified",
                               "git_repository": "required_not_verified" if provider == "codex" else "not_required_by_this_profile",
                               "cli_version_flags": "required_not_verified",
                               "auth_billing_route": "required_not_verified"},
        "isolation": {"guaranteed": False, "ambient_config": "not_inspected", "ambient_plugins": "not_inspected",
                      "ambient_skills": "not_inspected", "ambient_rules": "not_inspected", "auth": "not_read",
                      "sandbox": sandbox if provider == "codex" else "not_configured_by_planner"},
        "warnings": ["cwd does not isolate user configuration, plugins, skills, rules, auth or public answers",
                     "version/model identifiers are caller supplied; aliases are not resolved",
                     "permission-denied operations can fail; approval policy is not a security sandbox",
                     "no token/time/cost budget enforcement in this phase",
                     "independent prepared workspace required; planner cannot attest preparation/provenance"],
    }
    if provider == "codex":
        result["warnings"].append("Codex requires a Git repository; prepared directories may lack .git. Operator must prepare a dedicated repository before any future execution; git checks are not bypassed")
    if provider == "claude":
        result["warnings"].append("bare is not enabled: it can disable subscription/OAuth auth; MCP/tool availability is not restricted by this plan")
    result["plan_sha256"] = sha256(canonical(result))
    return result
