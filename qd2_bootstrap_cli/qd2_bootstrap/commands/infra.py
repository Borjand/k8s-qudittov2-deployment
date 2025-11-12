import typer
app = typer.Typer(no_args_is_help=True)

@app.command()
def status():
    typer.echo("[infra] status: stub")

# add plan/apply/destroy later
