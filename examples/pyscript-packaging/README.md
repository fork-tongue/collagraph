# PyScript packaging example

In the root:

```sh
poetry build
cp dist/*.whl examples/pyscript-packaging/deps/.
python -m http.server --directory examples/pyscript-packaging
```

In this folder:

```sh
poetry build
```

Then go to: http://localhost:8000/index.html
