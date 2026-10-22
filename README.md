# icon-radix

[Radix Icons](https://github.com/radix-ui/icons) as 332 pre-rendered, 15×15 `CrImage` constants for Crystal.

```yaml
dependencies:
  icon-radix:
    github: kojix2/icon-radix
```

```crystal
require "icon-radix"

icon = Icon::Radix::Gear
```

Constants are shared, mutable images; copy before editing. PNG data lives in `src/data/icons.tsv` and is loaded by a Crystal macro.

## Regenerate

Requires Python 3, librsvg, Cairo, and a ZIP of the upstream repository.

```bash
python3 scripts/generate.py /path/to/icons-main.zip
python3 scripts/generate.py /path/to/icons-main.zip --check
```

MIT: [shard](LICENSE), [upstream icons](LICENSE.radix).
