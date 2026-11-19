import copy
import json

import pytest


@pytest.fixture
def records():
    server = {
        "id": "101",
        "server_name": "db-example",
        "status": "active",
        "mysql_version": "8.0.40",
        "agent_version": "1.0",
        "instance_type": "1",
        "releem_score": 70,
        "ip_address": "192.0.2.8",
        "users": [{"email": "private@example.invalid", "role": "viewer"}],
    }
    rec = {
        "id": 601,
        "server_id": "101",
        "source_type": "configuration",
        "source_id": "501",
        "source_subtype": "buffer_pool",
        "title": "Review buffer pool",
        "summary": "Consider the measured memory demand",
        "status": "done",
        "priority_score": 90,
        "type_id": 3,
        "category_id": 3,
        "type": {"id": 3, "name": "Untrusted type label"},
        "category": {"id": 3, "name": "Untrusted category label"},
        "why_important_now": "Memory pressure",
        "evidence": {"href": "https://untrusted.example.invalid/leak", "pointer": None},
    }
    return copy.deepcopy(
        {
            "/v1/servers": [server],
            "/v1/servers/101": server,
            "/v1/servers/101/details": {
                "id": "101",
                "health_checks": {},
                "security_checks": {},
                "security_checks_unknown": ["future_code"],
                "security_checks_decode_error": "unsupported_failure_codes",
            },
            "/v1/servers/101/health-checks": {"timestamp": None, "checks": {}},
            "/v1/servers/101/security-checks": {
                "timestamp": 1794339000,
                "checks": {
                    "accounts": {"failed": True, "description": "Account finding", "value": None}
                },
                "failed_checks": ["accounts"],
                "security_checks_score": 70,
            },
            "/v1/servers/101/recommendations": {
                "items": [rec],
                "total": 1,
                "limit": 20,
                "offset": 0,
            },
            "/v1/servers/101/recommendations/601": {
                **rec,
                "current_review": {
                    "id": 501,
                    "priority_score": 90.0,
                    "why_important_now": "Measured demand",
                    "review_details": {"password": "synthetic-secret"},
                },
                "status_history": [
                    {
                        "id": 701,
                        "actor_type": "user",
                        "actor_id": "private@example.invalid",
                        "new_status": "done",
                    }
                ],
            },
        }
    )


@pytest.fixture
def query_records(records):
    records.update(
        {
            "/v1/servers/101/query-analytics": {
                "start_time": "2026-11-09T00:00:00",
                "end_time": "2026-11-10T00:00:00",
                "items": [
                    {
                        "rid": "run-1",
                        "schema_name": "app db",
                        "query_id": "abc123",
                        "calls": 20.0,
                        "avg_time_ms": None,
                        "sum_time_sec": 3.0,
                        "sum_time_perc_total": 25.0,
                        "sum_time_perc_first": 100.0,
                        "query": "SELECT private_literal FROM customer",
                        "query_text": "secret SQL",
                    }
                ],
            },
            "/v1/servers/101/query-optimizations": {
                "items": [
                    {
                        "id": 501,
                        "server_id": 101,
                        "status": 777,
                        "timestamp_status": 1794268800,
                        "schema_name": "app db",
                        "query_id": "abc123",
                        "query_text": "secret SQL",
                        "before_calls": None,
                        "before_avg_time_ms": None,
                    },
                ]
            },
            "/v1/servers/101/query-optimizations/501": {
                "id": 501,
                "server_id": 101,
                "status": 5,
                "timestamp_status": 1794268800,
                "schema_name": "app db",
                "query_id": "abc123",
                "query_explain": None,
                "recommendation": "ALTER TABLE private_table ADD ...",
                "recommendations": [],
            },
            "/v1/servers/101/query-analytics/app db/abc123/recommendations": {
                "items": [
                    {
                        "rid": "analysis-2",
                        "schema_name": "app db",
                        "query_id": "abc123",
                        "title": "Investigate access path",
                        "type": "LOOKUP_SPEED",
                        "impact_score": "high",
                        "sql": "CREATE INDEX private ON customer ...",
                        "modified_query": "private SQL",
                        "explain": json.dumps(
                            {
                                "Plan": {
                                    "Node Type": "Seq Scan",
                                    "Plan Rows": 100,
                                    "Filter": "email='private@example.invalid'",
                                }
                            }
                        ),
                        "timestamp": "2026-11-10T00:00:00Z",
                    },
                ]
            },
        }
    )
    return records
