# icon-radix

[Radix Icons](https://github.com/radix-ui/icons) as 332 pre-rendered, 15×15 `CrImage` constants for Crystal.

```yaml
dependencies:
  icon-radix:
    github: kojix2/icon-radix
```

```crystal
require "icon-radix"

gear = Icon::Radix::Gear
```

Constants are shared, mutable images. Copy an icon before editing it.

## Regenerate

Maintainers need Python 3, librsvg, Cairo, and the source ZIP pinned in [generate.py](scripts/generate.py).

```bash
python3 scripts/generate.py /path/to/icons-main.zip
python3 scripts/generate.py /path/to/icons-main.zip --check
```

This shard is MIT licensed under [LICENSE](LICENSE). The bundled Radix icons retain the upstream [LICENSE.radix](LICENSE.radix).
