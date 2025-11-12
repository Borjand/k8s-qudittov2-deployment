import typer
import yaml
from pathlib import Path
from rich import print as rprint
from qd2_bootstrap.models.quditto_deploy_spec import QudittoDeploySpec

app = typer.Typer(no_args_is_help=True)

@app.command()
def deploy(
    file: Path = typer.Option(..., "--file", "-f", exists=True, readable=True, help="Quditto deploy spec (YAML)"),
    namespace: str = typer.Option(None, "--namespace", help="Override 'namespace' from the spec"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without applying changes"),
):
    """
    Read the Quditto deploy spec (YAML), validate it with Pydantic, and print a deployment plan.
    This is a stub: it does *not* talk to Kubernetes nor Helm yet.
    """
    # 1) Load YAML into a Python dict.
    try:
        data = yaml.safe_load(file.read_text())
    except Exception as e:
        rprint(f"[bold red]Failed to read YAML:[/] {e}")
        raise typer.Exit(code=2)

    # 2) Validate the structure and names using Pydantic.
    try:
        spec = QudittoDeploySpec.model_validate(data)
    except Exception as e:
        rprint(f"[bold red]Spec validation error:[/] {e}")
        raise typer.Exit(code=2)

    # 3) Resolve effective namespace (CLI override has priority).
    ns = namespace or spec.namespace or "(not set)"

    # 4) Print a human-friendly plan. Later we’ll map this into Helm values.
    rprint("[bold cyan]Quditto deployment plan (dry stub)[/]")
    rprint(f"  Namespace      : {ns}")

    rprint("\n[bold]Placement[/]")
    rprint(f"  qcontroller    -> node: {spec.qcontroller.nodek8s}")
    if spec.qorchestrator:
        rprint(f"  qorchestrator  -> node: {spec.qorchestrator.nodek8s}")
    else:
        rprint("  qorchestrator  : (not specified)")

    if spec.qnodes:
        for qn in spec.qnodes:
            rprint(f"  {qn.name:<14} -> node: {qn.nodek8s}")
    else:
        rprint("  qnodes         : (none)")

    rprint(f"\n  Dry-run: {dry_run}")
    rprint("[green]No changes applied (stub).[/]")
