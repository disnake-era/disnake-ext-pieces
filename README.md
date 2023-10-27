<!-- SPDX-License-Identifier: LGPL-3.0-only -->

# disnake-ext-pieces

Bot modularization, done right.

> Note: this project was originally a fork of [disnake-ext-plugins](https://github.com/Chromosologist/disnake-ext-plugins).
> At some point my childish brain decided it would be cool to rebrand - that's how -plugins turned into -pieces - but stuff has changed since then and -pieces will no longer be maintained as a disnake extension.
> Therefore, for long-term projects it is recommended to use the original -plugins instead.

## Example

```py
import disnake
from disnake.ext import commands, pieces


piece = pieces.Piece()


@piece.slash_command()
async def my_command(inter: disnake.CommandInteraction):
    await inter.response.send_message("Woo!")


setup, teardown = piece.create_extension_handlers()
```

See [`./example`](./example) for an example.

## Version Guarantees

This project obeys the [Cargo SemVer](https://doc.rust-lang.org/cargo/reference/semver.html).

## License

This project is licensed under the GNU Lesser General Public License, version 3; see
[LICENSE](./LICENSE) for more.

## Acknowledgements

This project has portions of other software incorporated into it; please read
[ACKNOWLEDGEMENTS.md](./ACKNOWLEDGEMENTS.md) for more.
