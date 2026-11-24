"""Compare state-local snapshots and publish reviewed setting names and scalar values."""

import json
import re
from collections.abc import Iterable
from decimal import Decimal
from fractions import Fraction
from typing import Any

from ..api.diagnostic_models import ConfigurationDetail
from .redaction import Redactor

BYTE_SETTINGS = frozenset(
    """
    innodb_buffer_pool_size innodb_buffer_pool_chunk_size innodb_redo_log_capacity
    innodb_log_file_size innodb_log_buffer_size tmp_table_size max_heap_table_size
    temptable_max_ram temptable_max_mmap join_buffer_size sort_buffer_size read_buffer_size
    read_rnd_buffer_size key_buffer_size thread_stack bulk_insert_buffer_size
    myisam_sort_buffer_size query_cache_size query_cache_limit query_cache_min_res_unit
    transaction_prealloc_size max_allowed_packet
""".split()
)
NUMERIC_SETTINGS = BYTE_SETTINGS | frozenset(
    """
    max_connections table_open_cache table_definition_cache thread_cache_size
    open_files_limit innodb_buffer_pool_instances innodb_log_files_in_group
    innodb_io_capacity innodb_io_capacity_max innodb_read_io_threads innodb_write_io_threads
    innodb_flush_log_at_trx_commit innodb_flush_neighbors innodb_lru_scan_depth
    innodb_page_cleaners innodb_thread_concurrency innodb_purge_threads
    innodb_max_dirty_pages_pct innodb_max_dirty_pages_pct_lwm
    sync_binlog binlog_expire_logs_seconds expire_logs_days long_query_time
    max_digest_length performance_schema_max_digest_length max_prepared_stmt_count
    wait_timeout interactive_timeout connect_timeout lock_wait_timeout
    innodb_lock_wait_timeout query_cache_type
""".split()
)
BOOLEAN_SETTINGS = frozenset(
    """
    innodb_adaptive_hash_index innodb_file_per_table innodb_doublewrite
    log_bin performance_schema skip_name_resolve slow_query_log
""".split()
)
ENUM_SETTINGS = {
    "innodb_flush_method": frozenset(
        {"fsync", "o_direct", "o_direct_no_fsync", "o_dsync", "littlesync", "nosync"}
    ),
    "innodb_change_buffering": frozenset(
        {"none", "inserts", "deletes", "changes", "purges", "all"}
    ),
    "innodb_doublewrite": frozenset({"detect_only", "detect_and_recover"}),
    "binlog_format": frozenset({"row", "statement", "mixed"}),
    "query_cache_type": frozenset({"off", "on", "demand"}),
}
PLAIN = r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:e[+-]?[0-9]{1,3})?"
NUMBER = re.compile(PLAIN, re.ASCII | re.I)
BYTES = re.compile(rf"({PLAIN}) *(?:([kmgtpe])(?:i?b)?|b)", re.ASCII | re.I)
TRUE = frozenset({"1", "on", "yes", "true"})
FALSE = frozenset({"0", "off", "no", "false"})
NOT_A_VALUE = frozenset({"", "null", "nan", "inf", "+inf", "-inf", "infinity"})


def _normalized(name: str, value: str) -> Fraction | str:
    folded = value.lower()
    if name in BOOLEAN_SETTINGS:
        if folded in TRUE:
            return Fraction(1)
        if folded in FALSE:
            return Fraction(0)
    if name in NUMERIC_SETTINGS and NUMBER.fullmatch(value):
        return Fraction(Decimal(value))
    if name in BYTE_SETTINGS and (match := BYTES.fullmatch(value)):
        number, unit = match.groups()
        factor = 1024 ** ("kmgtpe".index(unit.lower()) + 1) if unit else 1
        return Fraction(Decimal(number)) * factor
    return folded if name in ENUM_SETTINGS else value


def _scalar(value: Any) -> str | None:
    if not isinstance(value, (str, int, float, bool)):
        return None
    value = str(value).strip()
    return value if len(value) <= 64 and value.lower() not in NOT_A_VALUE else None


def _named_values(pairs: Iterable[tuple[str, Any]]) -> dict[str, str | None]:
    values: dict[str, str | None] = {}
    for key, raw in pairs:
        name = key.strip().lower()
        if not name:
            continue
        value = _scalar(raw)
        if name in values:
            previous = values[name]
            if (
                previous is None
                or value is None
                or (_normalized(name, previous) != _normalized(name, value))
            ):
                values[name] = None
        else:
            values[name] = value
    return values


def _snapshot(raw: Any) -> dict[str, str | None] | None:
    if isinstance(raw, str):
        # Keep duplicate JSON keys observable. Nested objects stay non-scalar.
        try:
            raw = json.loads(raw, object_pairs_hook=_named_values)
        except (ValueError, RecursionError):
            return None
        return raw if isinstance(raw, dict) else None
    return _named_values(raw.items()) if isinstance(raw, dict) else None


def _publishable(name: str, value: str, redactor: Redactor) -> bool:
    if redactor.has_sensitive_text(value) or redactor.has_sensitive_text(name):
        return False
    return isinstance(_normalized(name, value), Fraction) or (
        value.lower() in ENUM_SETTINGS.get(name, ())
    )


def _comparison(
    before: dict[str, str | None] | None,
    after: dict[str, str | None] | None,
    redactor: Redactor,
    *,
    targets_only: bool = False,
    fields: tuple[str, str] = ("old_value", "new_value"),
    targets: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"status": "unavailable", "items": [], "uncompared": 0, "omitted": 0}
    if before is None or after is None:
        return result
    if targets_only and (targets or after) and (not before or (targets is not None and not after)):
        return result
    names: Iterable[str]
    if targets is not None:
        names = targets.keys()
    elif targets_only:
        names = after.keys()
    else:
        names = before.keys() | after.keys()
    for name in sorted(names):
        old, new = before.get(name), after.get(name)
        target = targets.get(name) if targets is not None else new
        if old is None or new is None or target is None:
            result["uncompared"] += 1
            continue
        expected = _normalized(name, target)
        if _normalized(name, old) == expected or _normalized(name, new) != expected:
            continue
        if not all(_publishable(name, value, redactor) for value in (old, new, target)):
            result["omitted"] += 1
            continue
        result["items"].append({"name": name, fields[0]: old, fields[1]: new})
    result["status"] = "partial" if result["uncompared"] or result["omitted"] else "complete"
    return result


class ConfigurationChanges:
    def __init__(self, state: ConfigurationDetail, redactor: Redactor) -> None:
        self.original = _snapshot(state.variables_orig)
        self.recorded = _snapshot(state.source_variables)
        self.targets = _named_values(
            (variable.name, variable.value) for variable in state.variables
        )
        self.redactor = redactor

    def detail(self, state: ConfigurationDetail) -> dict[str, dict[str, Any]]:
        changes = {
            "recorded": _comparison(self.original, self.recorded, self.redactor),
            "proposed": _comparison(self.original, self.targets, self.redactor, targets_only=True),
        }
        if state.applied_status in {0, 2}:
            changes["remaining"] = _comparison(
                self.recorded,
                self.targets,
                self.redactor,
                targets_only=True,
                fields=("last_recorded_value", "recommended_value"),
            )
        return changes

    def applied(self) -> dict[str, Any]:
        return _comparison(
            self.original, self.recorded, self.redactor, targets_only=True, targets=self.targets
        )
