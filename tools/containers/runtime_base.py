"""Build-time removal of unused SQLite, retaining APK's real dependency metadata."""

import shutil
import subprocess
import sysconfig
from pathlib import Path

SQLITE = "so:libsqlite3.so.0"


def requirements(installed: str) -> list[str]:
    packages = [
        block for block in installed.split("\n\n") if "P:.python-rundeps" in block.splitlines()
    ]
    if len(packages) != 1:
        raise ValueError("Unexpected Python base dependency package")
    fields = [line[2:] for line in packages[0].splitlines() if line.startswith("D:")]
    if len(fields) != 1 or SQLITE not in fields[0].split():
        raise ValueError("Unexpected Python shared-library dependencies")
    return [dependency for dependency in fields[0].split() if dependency != SQLITE]


def main() -> None:
    dependencies = requirements(Path("/lib/apk/db/installed").read_text())
    subprocess.run(  # noqa: S603 -- dependencies from the pinned official base metadata
        ["/sbin/apk", "add", "--no-cache", "--virtual", ".mcp-python-rundeps", *dependencies],
        check=True,
    )
    subprocess.run(["/sbin/apk", "del", ".python-rundeps", "sqlite-libs"], check=True)  # noqa: S603
    stdlib = Path(sysconfig.get_path("stdlib"))
    wrapper = stdlib / "sqlite3"
    extensions = list((stdlib / "lib-dynload").glob("_sqlite3*.so"))
    if not wrapper.is_dir() or len(extensions) != 1:
        raise ValueError("Unexpected Python SQLite layout")
    shutil.rmtree(wrapper)
    extensions[0].unlink()
    subprocess.run(  # noqa: S603 -- fixed security-patched stable repository versions
        ["/sbin/apk", "add", "--no-cache", "krb5-libs=1.22.3-r0", "zlib=1.4-r0"],
        check=True,
    )


if __name__ == "__main__":
    main()
