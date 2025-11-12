import typer
app = typer.Typer(no_args_is_help=True)

@app.command()
def status():
    typer.echo("[cluster] status: stub")

# add create/upgrade/delete later
