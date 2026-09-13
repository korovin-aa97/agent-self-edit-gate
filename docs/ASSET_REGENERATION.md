# Campaign asset regeneration

These commands regenerate the launch visuals without private repositories,
host paths, credentials, or network data. Run them from the repository root.

## Terminal cast and GIF

Prerequisites: Python 3.12+, the project development environment, and
[`agg` 1.9.0](https://github.com/asciinema/agg/releases/tag/v1.9.0). The checked-in
GIF uses macOS Menlo from `/System/Library/Fonts`.

The generator creates a disposable root, runs the real local `v0.1.3` CLI for
the allowed edit, denied authority path, and receipt verification, then checks
every exit code and complete output line. It fixes only presentation timing and
replaces the random 32-hex operation ID with `<operation-id>`.

```bash
uv run python examples/generate_demo_cast.py
agg --quiet --no-loop --theme github-dark \
  --font-dir /System/Library/Fonts --font-family Menlo \
  --font-size 17 --cols 96 --rows 18 --fps-cap 20 \
  --last-frame-duration 2.8 \
  docs/assets/demo.cast docs/assets/demo.gif
```

Verify that a fresh execution produces the exact checked-in cast:

```bash
uv run python examples/generate_demo_cast.py --check
```

The cast ends at 14.2 seconds; the final GIF frame adds 2.8 seconds, for a
17-second non-looping demo. Check the delivered GIF independently:

```bash
ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 docs/assets/demo.gif
```

Expected duration: `17.000000` seconds. With `agg` 1.9.0 and Menlo, the checked-in
GIF is `1003×452` with 10 frames. Visually confirm that it shows, in order,
`mutable`, `updated`, `E_ZONE_DENIED`, and `valid: 1 operations, 2 records`, with
no clipped lines or machine-specific paths.

## Static cards

The SVG files are canonical. Render the PNG copies with macOS `sips`:

```bash
sips -s format png docs/assets/launch-card.svg \
  --out docs/assets/launch-card.png
sips -s format png docs/assets/square-card.svg \
  --out docs/assets/square-card.png
```

Verify XML and exact dimensions:

```bash
xmllint --noout docs/assets/launch-card.svg docs/assets/square-card.svg
sips -g pixelWidth -g pixelHeight \
  docs/assets/launch-card.png docs/assets/square-card.png
```

Expected PNG dimensions are `1200×630` and `1080×1080`. Also inspect each PNG
at native size and scaled to 320 pixels wide; text must remain separate from
icons and the `NOT A SANDBOX` boundary must remain legible.
