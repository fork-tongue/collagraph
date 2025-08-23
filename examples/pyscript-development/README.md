# PyScript development example

This example demonstrates how to set up a development environment
for collagraph's domrenderer/pyscript support.

This setup is most suitable for local development on collagraph.

In root of project:

```sh
uv build
cp dist/*.whl examples/pyscript/deps/.
python -m http.server --directory examples/pyscript
```

Then go to: http://localhost:8000/pyscript.html

## Bonus tips

I use `entr` to watch files in the collagraph repo to build the new
`.whl` file on every change and then copy the wheel to the 
`examples/pyscript/deps/` folder:

```sh
# Run uv build when any .py or .cgx file changes
find . -iname "*.py" -o -iname "*.cgx" | entr -c uv build
```

```sh
# Copy the .whl file to deps folder when the whl is updated
find dist -iname "*.whl" | entr -c cp -v dist/*.whl examples/pyscript/deps/.
```
