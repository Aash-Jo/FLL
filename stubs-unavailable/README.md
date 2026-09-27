# Stubs for APIs this hub does not have

Stubs parked here are **deliberately outside `typings/`** so Pylance does not
offer them. They describe modules that LEGO documents but that Hub OS 1.8.149
does not actually expose.

## `app/`

`import app` raises `ImportError: no module named 'app'` on this hub, and `app`
does not appear in `help('modules')`. Confirmed twice over the serial REPL,
including every submodule the stubs cover: `app.display`, `app.music`,
`app.sound`, `app.bargraph`, `app.linegraph`.

The stubs came from `jvolkening/lego-spike-python-v3-docs`, generated from
LEGO's help content - which documents a newer Hub OS than this hub runs. Left
here rather than deleted: if a firmware update adds the module, move the folder
back into `typings/` and it works again.

These modules drive the SPIKE app's own UI panels (graphs, sound library), so
they may behave differently when a program runs inside the app rather than
standalone. That has not been tested here. Verify before relying on them:

```bash
py -m mpremote connect id:335234693132 exec "import app; print(app)"
```
