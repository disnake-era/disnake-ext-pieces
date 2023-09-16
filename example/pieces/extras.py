# SPDX-License-Identifier: LGPL-3.0-only

from disnake.ext import commands, pieces

# Sometimes you would want to attach some extra info to your plugin and grab
# it back later in another command. For this, the so-called extras exist.
# They don"t serve any actual purpose and are purely for use by the user.
# They can also be used as a lightweight state for, e.g., components.

extras_piece: pieces.Piece[commands.Bot] = pieces.Piece(extras = { "foo": "bar"})

# Afterwards we can easily access this data.


@extras_piece.command()
async def what_is_what(ctx: commands.Context[commands.Bot]) -> None:
    await ctx.reply(str(extras_piece.extras))


# Likewise you can change this data at runtime.


@extras_piece.listener("on_message")
async def swap_foobar(ctx: commands.Context[commands.Bot]) -> None:
    if extras_piece.extras.get("foo"):
        extras_piece.extras = { "bar": "foo"}
    else:
        extras_piece.extras = { "foo": "bar"}

    await ctx.reply("Done!")


setup, teardown = extras_piece.create_extension_handlers()
