# SPDX-License-Identifier: LGPL-3.0-only

import disnake
from disnake.ext import commands, pieces

# Create a basic plugin...
# Without providing any extra data, a plugin will be instantiated with only a
# name. This name will default to the file in which the plugin was created.
# In this case, a plugin named "basic" would be created.

# Also note that type annotation here is *mandatory*. Since in our `main.py`
# we use `commands.Bot`, we specify it here as well.
# If you're wondering why: Python does not support TypeVar defaults, and while
# Python does indeed have a PEP for this (696), it's scheduled for 3.12, and
# since we aim to support all supported Python versions, we will not be able
# to use this feature until at least 24 Oct 2027 (see https://endoflife.date/python).

basic_piece: pieces.Piece[commands.Bot] = pieces.Piece()

# Next, we register a command on the plugin.
# This is very similar to creating commands normally, but we now use the
# `@Plugin.command()` decorator to register the command on the plugin.


@basic_piece.command()
async def my_command(ctx: commands.Context[commands.Bot]) -> None:
    await ctx.reply("hi!")


# Similarly, we can register slash, user, and message commands.
# Plugins also support listeners as per usual:


@basic_piece.listener("on_message")
async def my_listener(msg: disnake.Message) ->...:
    ...


# Just like any other type of disnake extension, if we wish to load this from
# the main file using `Bot.load_extension()`, we need to define `setup` and
# `teardown` functions. Plugins provide a simple way of making these functions:

setup, teardown = basic_piece.create_extension_handlers()

# This will simply call `basic_plugin.load()` in setup and `basic_plugin.unload()`
# in teardown, though wrapped inside asyncio tasks, as these functions are async.
