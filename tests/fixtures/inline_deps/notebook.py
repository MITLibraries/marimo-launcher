# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo",
#     "tinydb",
# ]
# ///

import marimo

__generated_with = "0.14.17"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md(
        r"""
    # Hello World!

    This notebook exercises launch via a Docker container.
    """
    )
    return


@app.cell
def _(mo):
    import sys

    mo.md(f"""Python version: `{sys.version}`""")
    return


@app.cell
def _(mo):
    import tempfile
    from tinydb import TinyDB, Query

    with tempfile.TemporaryDirectory() as tmpdir:
        db = TinyDB(f"{tmpdir}/db.json")
        db.insert({"name": "test"})
        results = db.all()

    mo.md(
        f"""
    TinyDB loaded: `OK`<br>
    Results: `{results}`
    """
    )
    return


if __name__ == "__main__":
    app.run()
