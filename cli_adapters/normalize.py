"""Offline JSONL summaries, not trial records or correctness judgements."""
from .common import AdapterError, MAX_TRACE_BYTES, canonical, nonnegative, sha256, strict_json

KNOWN_CODEX = {"thread.started", "turn.started", "turn.completed", "turn.failed", "item.started", "item.updated", "item.completed", "error"}
KNOWN_CLAUDE = {"system", "assistant", "user", "result", "stream_event", "tool_progress", "auth_status", "rate_limit_event"}
USAGE_CODEX = {"input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens", "reasoning_output_tokens"}
USAGE_CLAUDE = {"input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"}


def normalize(provider, raw, *, model, cli_version, data_class="unverified_external_trace"):
    if provider not in {"codex", "claude"}:
        raise AdapterError("provider must be codex or claude")
    if data_class not in {"synthetic_test_fixture", "unverified_external_trace"}:
        raise AdapterError("offline normalization cannot attest actual agent trials")
    if not isinstance(raw, bytes) or len(raw) > MAX_TRACE_BYTES:
        raise AdapterError("trace must be bytes no larger than 16 MiB")
    if not isinstance(model, str) or not model.strip() or not isinstance(cli_version, str) or not cli_version.strip():
        raise AdapterError("caller-declared model and CLI version required")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AdapterError("trace is not UTF-8") from exc
    events, warnings, terminals = [], [], []
    unknown_types = set()
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = strict_json(line)
        except AdapterError as exc:
            raise AdapterError("line %d: %s" % (number, exc)) from exc
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise AdapterError("line %d: event object with string type required" % number)
        kind = event["type"]
        events.append(event)
        known = KNOWN_CODEX if provider == "codex" else KNOWN_CLAUDE
        if kind not in known:
            unknown_types.add(kind)
        if (provider == "codex" and kind in {"turn.completed", "turn.failed"}) or (provider == "claude" and kind == "result"):
            terminals.append(event)
    # A partial first run followed by a complete second run is not one trial.
    # Missing start records remain acceptable for externally truncated traces, but
    # conflicting identities or repeated starts must never silently drop usage.
    if provider == "codex":
        for start_type in ("thread.started", "turn.started"):
            if sum(event["type"] == start_type for event in events) > 1:
                raise AdapterError("ambiguous trace: repeated " + start_type)
    elif sum(event["type"] == "system" and event.get("subtype") == "init" for event in events) > 1:
        raise AdapterError("ambiguous trace: repeated Claude session init")
    identity_key = "thread_id" if provider == "codex" else "session_id"
    identities = set()
    for event in events:
        if identity_key in event:
            if not isinstance(event[identity_key], str) or not event[identity_key]:
                raise AdapterError("invalid trace session identity")
            identities.add(event[identity_key])
    if len(identities) > 1:
        raise AdapterError("ambiguous trace: conflicting session identities")
    terminal = terminals[0] if terminals else None
    if any(canonical(item) != canonical(terminal) for item in terminals[1:]):
        raise AdapterError("ambiguous trace: inconsistent multiple terminal records; do not merge sessions/turns")
    if len(terminals) > 1:
        warnings.append("identical duplicate terminal records deduplicated; usage counted once")
    if unknown_types:
        warnings.append("unknown event types retained in raw trace: " + ", ".join(sorted(unknown_types)))
    # Only authoritative turn/result totals are consumed. Item/message/stream usage
    # may overlap cumulatively and is never summed into these totals.
    usage_fields = USAGE_CODEX if provider == "codex" else USAGE_CLAUDE
    usage = {field: None for field in sorted(usage_fields)}
    cost = None
    outcome = "incomplete"
    if terminal is not None:
        if provider == "codex":
            outcome = "completed" if terminal["type"] == "turn.completed" else "failed"
        else:
            subtype, is_error = terminal.get("subtype"), terminal.get("is_error")
            if not isinstance(subtype, str) or not isinstance(is_error, bool):
                raise AdapterError("Claude result requires subtype string and is_error boolean")
            outcome = "completed" if subtype == "success" and not is_error else "failed"
            if terminal.get("total_cost_usd") is not None:
                cost = nonnegative(terminal["total_cost_usd"], "total_cost_usd")
        raw_usage = terminal.get("usage")
        if raw_usage is not None:
            if not isinstance(raw_usage, dict):
                raise AdapterError("terminal usage must be an object or null")
            for field in usage:
                if raw_usage.get(field) is not None:
                    usage[field] = nonnegative(raw_usage[field], field, integer=True)
            if raw_usage.keys() - usage_fields:
                warnings.append("additional terminal usage fields retained in terminal_metadata; not aggregated")
        if provider == "codex" and usage["cached_input_tokens"] is not None and usage["input_tokens"] is not None and usage["cached_input_tokens"] > usage["input_tokens"]:
            raise AdapterError("cached input exceeds total Codex input")
    # Final result must be last semantic event. Identical retransmission is allowed;
    # later substantive records make truncation/session concatenation ambiguous.
    if terminals:
        first = next(i for i, item in enumerate(events) if item is terminal)
        for later in events[first + 1:]:
            if canonical(later) != canonical(terminal):
                raise AdapterError("ambiguous trace: nonterminal event after terminal")
    if not terminal:
        warnings.append("no terminal event; missing usage/cost are unknown, not zero")
    warnings.append("terminal completion is not a verified process exit; process status and exit code were not supplied")
    warnings.append("unknown fields are not interpreted; original bytes must be retained with raw_trace_sha256")
    return {
        "schema_version": 1, "run_kind": "offline_trace_normalization", "data_class": data_class,
        "provider": provider, "model": model, "cli_version": cli_version,
        "identity_provenance": "caller_declared_not_verified", "cli_outcome": outcome,
        "process_exit_code": None, "process_status": "not_supplied", "cli_outcome_basis": "terminal_event_only",
        "business_status": "not_evaluated", "analysis_record_ready": False,
        "raw_trace_sha256": sha256(raw), "raw_trace_bytes": len(raw), "event_count": len(events),
        "terminal_record_count": len(terminals), "unknown_event_types": sorted(unknown_types),
        "usage": usage, "usage_source": "terminal_only" if terminal else None,
        "usage_semantics": "Codex cached input is a subset of input; Claude cache read/write are separate input categories; never sum stream/message/modelUsage totals",
        "terminal_metadata": terminal, "cost_usd": cost,
        "cost_semantics": "cli_reported_estimate_not_verified_billing" if provider == "claude" and cost is not None else "unknown_not_reported",
        "cost_usd_unknown_reason": None if cost is not None else "CLI terminal did not supply total USD cost; subscription billing is not inferred",
        "elapsed_seconds": None, "elapsed_seconds_unknown_reason": "external wall-clock boundary not supplied; CLI duration fields are not substituted",
        "warnings": warnings,
    }
