"""Local filesystem client for cloud-init template management.

Mirrors the GiteaClient interface used for templates so callers need not
know the source.  Templates are read from a directory bind-mounted
read-only into the container at TEMPLATES_DIR (default /app/cloud-init).

Expected directory structure:
    cloud-init/
    ├── alpine/
    │   ├── minimal.yaml
    │   ├── database.yaml
    │   └── webserver.yaml
    ├── ubuntu/
    │   └── ...
    ├── debian/
    │   └── ...
    └── common/
        ├── hardening.sh
        └── setup_docker.sh
"""
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LocalTemplateClient:
    """Read cloud-init templates from the local filesystem."""

    COMMON_DIR = "common"

    def __init__(self, base_dir: str = "/app/cloud-init"):
        self.base_dir = Path(base_dir)
        logger.info(f"LocalTemplateClient initialised (base_dir={self.base_dir})")

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------

    async def get_file_content(self, path: str) -> str:
        """Read file at *path* relative to base_dir.

        Strips a leading ``cloud-init/`` prefix so callers that were
        previously building Gitea paths like
        ``cloud-init/alpine/minimal.yaml`` still work unchanged.
        """
        p = path.lstrip("/")
        if p.startswith("cloud-init/"):
            p = p[len("cloud-init/"):]

        full_path = self.base_dir / p
        if not full_path.is_file():
            raise FileNotFoundError(f"Template not found: {full_path}")

        content = full_path.read_text(encoding="utf-8")
        logger.debug(f"Read local template: {full_path} ({len(content)} bytes)")
        return content

    async def list_directory(self, path: str) -> List[Dict[str, Any]]:
        """List a directory relative to base_dir.

        Returns entries in the same dict format as GiteaClient so
        CloudInitGenerator (which calls list_directory + get_file_content)
        needs no changes.
        """
        p = path.lstrip("/")
        if p.startswith("cloud-init/"):
            p = p[len("cloud-init/"):]

        full_path = self.base_dir / p
        if not full_path.is_dir():
            return []

        entries = []
        for item in sorted(full_path.iterdir()):
            entries.append({
                "name": item.name,
                "path": str(item.relative_to(self.base_dir)),
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0,
            })
        return entries

    # ------------------------------------------------------------------
    # Template operations
    # ------------------------------------------------------------------

    async def get_template(self, os_type: str, template_name: str) -> str:
        """Read a cloud-init template by OS type and name."""
        if not template_name.endswith(".yaml"):
            template_name = f"{template_name}.yaml"
        full_path = self.base_dir / os_type / template_name
        if not full_path.is_file():
            raise FileNotFoundError(f"Template not found: {full_path}")
        return full_path.read_text(encoding="utf-8")

    async def list_templates(
        self, os_type: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """List available cloud-init templates, grouped by OS type."""
        result: Dict[str, List[str]] = {}

        if os_type:
            os_dir = self.base_dir / os_type
            if os_dir.is_dir():
                names = sorted(
                    f.stem
                    for f in os_dir.iterdir()
                    if f.is_file() and f.suffix == ".yaml"
                )
                result[os_type] = names
        else:
            for entry in sorted(self.base_dir.iterdir()):
                if entry.is_dir() and entry.name != self.COMMON_DIR:
                    names = sorted(
                        f.stem
                        for f in entry.iterdir()
                        if f.is_file() and f.suffix == ".yaml"
                    )
                    result[entry.name] = names

        return result

    # ------------------------------------------------------------------
    # Common scripts
    # ------------------------------------------------------------------

    async def list_common_scripts(self) -> List[str]:
        """List available common scripts (names without .sh extension)."""
        common_dir = self.base_dir / self.COMMON_DIR
        if not common_dir.is_dir():
            return []
        return sorted(
            f.stem
            for f in common_dir.iterdir()
            if f.is_file() and f.suffix == ".sh"
        )

    async def get_common_script(self, script_name: str) -> str:
        """Read a common script by name."""
        if not script_name.endswith(".sh"):
            script_name = f"{script_name}.sh"
        full_path = self.base_dir / self.COMMON_DIR / script_name
        if not full_path.is_file():
            raise FileNotFoundError(f"Script not found: {full_path}")
        return full_path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Lifecycle (no-ops — kept for interface compatibility)
    # ------------------------------------------------------------------

    def clear_cache(self):
        """No-op: local files have no in-memory cache."""

    async def ping(self) -> bool:
        """Return True if the templates directory exists and is readable."""
        return self.base_dir.is_dir()
