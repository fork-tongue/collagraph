# PyScript packaging example

This example demonstrates how to run a packaged collagraph-based
application directly in the browser with pyscript.

This setup is most suitable for deployment.

In this folder:

```sh
poetry build
python -m http.server
```

Then go to: http://localhost:8000/index.html

# Deploying

* Publish the wheel to pypi
* List the package name (instead of the local filepath) in the `<py-env>` tag
* Publish `index.html` to a webserver
* Your app is now publicly visible on your webserver
