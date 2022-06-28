# PyScript example

Instructions to run local dev version of collagraph:

In root of project:

```sh
poetry build
cp dist/*.whl examples/pyscript/deps/.
python -m http.server --directory examples/pyscript
```

Then go to: http://localhost:8000/pyscript.html


## Bonus tips:

I use `entr` to watch files in the collagraph repo to build the new
`.whl` file on every change and then copy the wheel to the 
`examples/pyscript/deps/` folder:

```sh
# Run poetry build when any .py or .cgx file changes
find . -iname "*.py" -o -iname "*.cgx" | entr -c poetry build
```

```sh
# Copy the .whl file to deps folder when the whl is updated
find dist -iname "*.whl" | entr -c cp -v dist/*.whl examples/pyscript/deps/.
```
