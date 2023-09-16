<!-- SPDX-License-Identifier: LGPL-3.0-only -->

# disnake-ext-pieces

Bot modularization, done right.

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
