"""Check the installed wheel from outside the source tree, without network access."""

import asyncio
import importlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

from artifacts import check_path
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from synthetic_api import KEY_A


async def check_stdio() -> dict[str, object]:
    parameters = StdioServerParameters(
        command="/opt/venv/bin/mcp-releem", env={"RELEEM_API_TOKEN": "synthetic-secret"}
    )
    async with Client(parameters, read_timeout_seconds=15) as client:
        tools = (await client.list_tools()).tools
        assert len(tools) == 10 and all(
            tool.annotations is not None and tool.annotations.read_only_hint for tool in tools
        )
        assert len((await client.list_prompts()).prompts) == 4
        prompt = await client.get_prompt("why_database_slow", {"server_id": "101"})
        content = prompt.messages[0].content
        assert content.type == "text" and "server_id=101" in content.text
        resource = (await client.read_resource("releem://reference")).contents[0]
        assert hasattr(resource, "text") and "hourly averages" in resource.text
        findings = next(tool for tool in tools if tool.name == "server_findings")
        assert findings.input_schema["properties"]["schema_limit"]["maximum"] == 100
        denied = await client.call_tool("execute_change", {})
        assert denied.is_error and denied.structured_content["error"]["code"] == "operation_denied"
        invalid = await client.call_tool("metrics", {"server_id": "101", "view": "series"})
        assert (
            invalid.is_error and invalid.structured_content["error"]["code"] == "invalid_arguments"
        )
        unavailable = await client.call_tool("metrics", {"server_id": "101"})
        offline_code = unavailable.structured_content["error"]["code"]
        assert unavailable.is_error and offline_code in {"dependency_unavailable", "timeout"}
        sensitive = await client.call_tool("captured_sessions", {"server_id": "101"})
        assert sensitive.is_error
        assert sensitive.structured_content["error"]["code"] == "sensitive_detail_disabled"
    synthetic = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).with_name("synthetic_stdio.py"))],
    )
    async with Client(synthetic, read_timeout_seconds=15) as client:
        result = await client.call_tool("servers", {"limit": 1})
        assert not result.is_error
        assert result.structured_content["data"]["items"][0]["id"] == "101"
        assert KEY_A not in result.model_dump_json()
        cancelled = False
        try:
            await asyncio.wait_for(
                client.call_tool("servers", {"hostname": ["cancel"]}), timeout=0.25
            )
        except TimeoutError:
            cancelled = True
        assert cancelled, "Synthetic slow request did not cancel"
        assert len((await client.list_tools()).tools) == 10
    process = subprocess.run(  # noqa: S603 - fixed installed executable
        ["/opt/venv/bin/mcp-releem"],
        env={"RELEEM_API_TOKEN": "synthetic-secret"},
        input="",
        text=True,
        capture_output=True,
        timeout=15,
    )
    assert process.returncode == 0 and process.stdout == ""
    return {
        "tools": len(tools),
        "read_only": True,
        "write_denied": True,
        "invalid_input_rejected": True,
        "offline_failure_explicit": True,
        "offline_failure_code": offline_code,
        "synthetic_read": True,
        "cancellation": True,
        "clean_stdio_eof": True,
    }


def main() -> None:
    mcp_releem = importlib.import_module("mcp_releem")
    assert mcp_releem.__file__ is not None
    expected = sys.argv[1]
    assert mcp_releem.__version__ == expected
    assert "/site-packages/" in str(Path(mcp_releem.__file__).resolve())
    environment = {"PATH": "/opt/venv/bin:/usr/bin:/bin", "RELEEM_API_TOKEN": "synthetic-secret"}
    for args in (["--version"], ["--check"]):
        result = subprocess.run(  # noqa: S603 - fixed installed executable
            ["/opt/venv/bin/mcp-releem", *args],
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0
        assert "synthetic-secret" not in result.stdout + result.stderr
        if args == ["--check"]:
            assert json.loads(result.stdout)["read_only"] is True
        else:
            assert result.stdout.strip() == expected
    hosted_module = importlib.import_module("mcp_releem.hosted.app")
    assert callable(hosted_module.create_hosted_app)
    hosted_environment = {
        "PATH": "/opt/venv/bin:/usr/bin:/bin",
        "RELEEM_MCP_PROFILE": "hosted",
        "RELEEM_MCP_PUBLIC_URL": "https://mcp.example.invalid/mcp",
    }
    for contaminated in (False, True):
        configured = dict(hosted_environment)
        if contaminated:
            configured["RELEEM_API_TOKEN"] = "synthetic-secret"  # noqa: S105 - synthetic fixture
        checked = subprocess.run(  # noqa: S603 - fixed installed executable
            ["/opt/venv/bin/mcp-releem", "--transport", "streamable-http", "--check"],
            env=configured,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert "synthetic-secret" not in checked.stdout + checked.stderr
        if contaminated:
            assert checked.returncode == 2 and not checked.stdout
        else:
            assert checked.returncode == 0
            state = json.loads(checked.stdout)
            assert state["profile"] == "hosted" and state["read_only"] is True
            assert state["global_customer_credential"] is False
    assert Path("/etc/alpine-release").is_file()
    assert importlib.util.find_spec("sqlite3") is None
    assert importlib.util.find_spec("_sqlite3") is None
    assert not list(Path("/usr/lib").glob("libsqlite3*"))
    package_records = Path("/lib/apk/db/installed").read_text()
    assert "P:apk-tools\n" in package_records
    assert "P:.mcp-python-rundeps\n" in package_records
    assert all(
        "P:" + name + "\n" not in package_records
        for name in (
            "sqlite-libs",
            "acl-libs",
            "systemd",
            "libsystemd",
            "libudev",
            "perl",
            "perl-base",
        )
    )
    assert os.getuid() != 0
    for root in (Path("/app"), Path(mcp_releem.__file__).parent):
        for path in root.rglob("*"):
            check_path(str(path.relative_to(root)))
    print(
        json.dumps(
            {
                "installed_wheel": True,
                "version": expected,
                "nonroot": True,
                "hosted_import_and_configuration": True,
                "runtime_os": "alpine",
                "unused_sqlite_removed": True,
                "os_package_metadata_retained": True,
                "stdio": asyncio.run(check_stdio()),
            }
        )
    )


if __name__ == "__main__":
    main()
