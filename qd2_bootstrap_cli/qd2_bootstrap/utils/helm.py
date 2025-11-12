import os
import shlex
import subprocess
from pathlib import Path
from typing import Iterable, Optional, List, Set
from rich import print as rprint

class HelmClient:
    """
    Thin wrapper around the Helm CLI.
    Keeps kubeconfig in env and provides typed methods.
    """

    def __init__(self, kubeconfig: Path):
        self.env = os.environ.copy()
        self.env["KUBECONFIG"] = str(kubeconfig)

    def _run(self, cmd: List[str]) -> int:
        rprint(f"[dim]$ {' '.join(shlex.quote(c) for c in cmd)}[/]")
        proc = subprocess.Popen(cmd, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="")
        return proc.wait()

    # ---------- repo ops ----------
    def repo_add(self, alias: str, url: str, force_update: bool = True) -> None:
        cmd = ["helm", "repo", "add", alias, url]
        if force_update:
            cmd.append("--force-update")
        self._run(cmd)
        self._run(["helm", "repo", "update"])

    # ---------- install/upgrade ----------
    def upgrade_install(
        self,
        release: str,
        chart_ref: str,
        namespace: str,
        version: Optional[str] = None,
        set_inline: Optional[Iterable[str]] = None,
        dry_run: bool = False,
        create_namespace: bool = True,
        extra_args: Optional[List[str]] = None,
    ) -> int:
        cmd = ["helm", "upgrade", "--install", release, chart_ref, "-n", namespace]
        if create_namespace:
            cmd.append("--create-namespace")
        if set_inline:
            for expr in set_inline:
                cmd += ["--set", expr]
        if version:
            cmd += ["--version", version]
        if dry_run:
            cmd += ["--dry-run", "--debug"]
        if extra_args:
            cmd += list(extra_args)
        return self._run(cmd)

    # ---------- query ----------
    def list_releases(self, namespace: str) -> Set[str]:
        """
        Return the set of release names currently present in a namespace.
        """
        cmd = ["helm", "list", "-n", namespace, "-q"]
        proc = subprocess.Popen(cmd, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, _ = proc.communicate()
        if proc.returncode != 0:
            return set()
        return set(line.strip() for line in out.splitlines() if line.strip())

    # ---------- uninstall ----------
    def uninstall(self, release: str, namespace: str, wait: bool = True, keep_history: bool = False, dry_run: bool = False) -> int:
        """
        Uninstall a release if present.
        NOTE: Helm 3 doesn't have a real --dry-run for uninstall; if dry_run=True, we just print the command and return 0.
        """
        if dry_run:
            rprint(f"[dim]$ helm uninstall {release} -n {namespace}{' --wait' if wait else ''}{' --keep-history' if keep_history else ''}  (dry-run) [/]")
            return 0
        cmd = ["helm", "uninstall", release, "-n", namespace]
        if wait:
            cmd.append("--wait")
        if keep_history:
            cmd.append("--keep-history")
        return self._run(cmd)
