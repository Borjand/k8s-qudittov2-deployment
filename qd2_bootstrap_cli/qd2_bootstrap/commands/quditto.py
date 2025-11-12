import typer
import yaml
from pathlib import Path
from rich import print as rprint
from rich.table import Table, box 

from qd2_bootstrap.models.quditto_deploy_spec import QudittoDeploySpec
from qd2_bootstrap.utils.mapping import values_from_params
from qd2_bootstrap.utils.merge import deep_merge
from qd2_bootstrap.utils.helm import HelmClient
from qd2_bootstrap.utils.helm_set import flatten_to_set_expressions

app = typer.Typer(no_args_is_help=True)

def _chart_ref(alias: str, chart: str) -> str:
    """Return full chart ref '<alias>/<chart>' unless already qualified."""
    return chart if "/" in chart else f"{alias}/{chart}"

@app.command()
def deploy(
    file: Path = typer.Option(..., "--file", "-f", exists=True, readable=True, help="Quditto deploy spec (YAML)"),
    kubeconfig: Path = typer.Option(..., "--kubeconfig", help="Path to kubeconfig for target cluster"),
    namespace: str = typer.Option(None, "--namespace", help="Override 'namespace' from the spec"),
    repo_alias: str = typer.Option("quditto", "--repo-alias", help="Local alias for the Helm repo"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Use Helm --dry-run (no changes)"),
    show_values: bool = typer.Option(False, "--show-values", help="Print merged Helm values per release"),
):
    """
    Validate spec, ensure Helm repo, and deploy only present components using --set inline.
    """
    # 1) Load + validate
    try:
        data = yaml.safe_load(file.read_text())
        spec = QudittoDeploySpec.model_validate(data)
    except Exception as e:
        rprint(f"[bold red]Spec validation error:[/] {e}")
        raise typer.Exit(code=2)

    ns = namespace or spec.namespace or "default"
    helm = HelmClient(kubeconfig=kubeconfig)

    # 2) Ensure Helm repo (this also validates reachability via 'helm repo update')
    helm.repo_add(repo_alias, spec.charts.repo, force_update=True)

    rprint("[bold cyan]Quditto deployment (inline --set)[/]")
    rprint(f"  Namespace : {ns}")
    rprint(f"  Helm repo : {spec.charts.repo}")

    # 3) Deploy qcontroller if present
    qc = spec.qudittoSetup.qcontroller
    if qc:
        qc_vals = deep_merge(qc.values, values_from_params(qc.nodek8s))
        qc_sets = flatten_to_set_expressions(qc_vals)
        chart_ref = _chart_ref(repo_alias, qc.chart)
        if show_values:
            rprint(f"\n[bold]Merged values for qcontroller ({chart_ref}@{qc.version or 'none'})[/]")
            rprint(yaml.safe_dump(qc_vals, sort_keys=False).rstrip())
        rprint("\n[bold]Applying release:[/] qcontroller")
        rc = helm.upgrade_install(
            release="qcontroller",
            chart_ref=chart_ref,
            namespace=ns,
            version=qc.version,
            set_inline=qc_sets,
            dry_run=dry_run,
        )
        if rc != 0:
            raise typer.Exit(code=rc)
    else:
        rprint("  qcontroller : (not specified)")

    # 4) Deploy qorchestrator if present
    qo = spec.qudittoSetup.qorchestrator
    if qo:
        qo_vals = deep_merge(qo.values, values_from_params(qo.nodek8s))
        qo_sets = flatten_to_set_expressions(qo_vals)
        chart_ref = _chart_ref(repo_alias, qo.chart)
        if show_values:
            rprint(f"\n[bold]Merged values for qorchestrator ({chart_ref}@{qo.version or 'none'})[/]")
            rprint(yaml.safe_dump(qo_vals, sort_keys=False).rstrip())
        rprint("\n[bold]Applying release:[/] qorchestrator")
        rc = helm.upgrade_install(
            release="qorchestrator",
            chart_ref=chart_ref,
            namespace=ns,
            version=qo.version,
            set_inline=qo_sets,
            dry_run=dry_run,
        )
        if rc != 0:
            raise typer.Exit(code=rc)
    else:
        rprint("  qorchestrator : (not specified)")

    # 5) Deploy qnodes if present
    if spec.qudittoSetup.qnodes:
        for qn in spec.qudittoSetup.qnodes:
            qn_vals = deep_merge(qn.values, values_from_params(qn.nodek8s))
            qn_sets = flatten_to_set_expressions(qn_vals)
            chart_ref = _chart_ref(repo_alias, qn.chart)
            if show_values:
                rprint(f"\n[bold]Merged values for {qn.name} ({chart_ref}@{qn.version or 'none'})[/]")
                rprint(yaml.safe_dump(qn_vals, sort_keys=False).rstrip())
            rprint(f"\n[bold]Applying release:[/] {qn.name}")
            rc = helm.upgrade_install(
                release=qn.name,
                chart_ref=chart_ref,
                namespace=ns,
                version=qn.version,
                set_inline=qn_sets,
                dry_run=dry_run,
            )
            if rc != 0:
                raise typer.Exit(code=rc)
    else:
        rprint("  qnodes : (none)")

    rprint("\n[green]Done.[/]")


@app.command()
def teardown(
    file: Path = typer.Option(..., "--file", "-f", exists=True, readable=True, help="Quditto deploy spec (YAML) used to infer release names"),
    kubeconfig: Path = typer.Option(..., "--kubeconfig", help="Path to kubeconfig for target cluster"),
    namespace: str = typer.Option(None, "--namespace", help="Override 'namespace' from the spec"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Do not prompt for confirmation"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print actions without applying changes"),
    keep_history: bool = typer.Option(False, "--keep-history", help="Pass --keep-history to helm uninstall"),
):
    """
    Uninstall Quditto releases found in the spec (only the components present in the YAML).
    """
    # 1) Load + validate spec
    try:
        data = yaml.safe_load(file.read_text())
        spec = QudittoDeploySpec.model_validate(data)
    except Exception as e:
        rprint(f"[bold red]Spec validation error:[/] {e}")
        raise typer.Exit(code=2)

    ns = namespace or spec.namespace or "default"
    helm = HelmClient(kubeconfig=kubeconfig)

    # 2) Build list of releases to uninstall, based on presence in YAML
    targets: list[str] = []
    if spec.qudittoSetup.qcontroller:
        targets.append("qcontroller")
    if spec.qudittoSetup.qorchestrator:
        targets.append("qorchestrator")
    for qn in spec.qudittoSetup.qnodes:
        targets.append(qn.name)

    if not targets:
        rprint("[yellow]Nothing to uninstall: no Quditto components found in the spec.[/]")
        raise typer.Exit(code=0)

    # 3) Show plan with installed status
    installed = helm.list_releases(ns)
    table = Table(title="Quditto teardown plan", box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Release")
    table.add_column("Namespace")
    table.add_column("Installed?")
    for rel in targets:
        table.add_row(rel, ns, "yes" if rel in installed else "no")
    rprint(table)

    if not yes:
        typer.confirm("Proceed to uninstall the releases above?", abort=True)

    # 4) Uninstall
    overall_rc = 0
    for rel in targets:
        if rel not in installed and not dry_run:
            rprint(f"[yellow]Skipping {rel}: not installed in namespace {ns}.[/]")
            continue
        rc = helm.uninstall(rel, namespace=ns, wait=True, keep_history=keep_history, dry_run=dry_run)
        if rc != 0:
            overall_rc = rc
            rprint(f"[bold red]Failed uninstall for {rel} (exit {rc}).[/]")

    if overall_rc != 0:
        raise typer.Exit(code=overall_rc)

    rprint("\n[green]Teardown complete.[/]")