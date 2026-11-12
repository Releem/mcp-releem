"""Inventory exact installed runtime packages and preserve bundled license notices."""

import importlib.metadata as metadata
import json
from pathlib import Path


def inventory() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for distribution in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
        if distribution.metadata["Name"] == "mcp-releem":
            continue
        notices = []
        for path in distribution.files or []:
            if "licenses" in path.parts or path.name.upper() in {
                "LICENSE",
                "LICENSE.TXT",
                "COPYING",
                "NOTICE",
            }:
                notices.append(
                    {
                        "path": str(path),
                        "text": Path(str(distribution.locate_file(path))).read_text(
                            errors="replace"
                        ),
                    }
                )
        records.append(
            {
                "name": distribution.metadata["Name"],
                "version": distribution.version,
                "license": distribution.metadata.get("License-Expression")
                or distribution.metadata.get("License"),
                "license_classifiers": [
                    v
                    for v in distribution.metadata.get_all("Classifier", [])
                    if v.startswith("License ::")
                ],
                "notices": notices,
            }
        )
    return records


if __name__ == "__main__":
    print(json.dumps(inventory(), indent=2))
