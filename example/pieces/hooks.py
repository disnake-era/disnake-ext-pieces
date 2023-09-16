# SPDX-License-Identifier: LGPL-3.0-only

import contextvars

import aiohttp

import disnake
from disnake.ext import commands, pieces

hooks_piece: pieces.Piece[commands.Bot] = pieces.Piece()

# Sometimes, it is desirable to attach extra behaviour to loading and unloading
# plugins. This can generally be achieved through the `setup` and `teardown`
# hooks. However, before disnake undergoes its inevitable async refactor to
# remain compatible with python 3.11, it can be slightly cumbersome to do so.
# For this purpose, plugins provide load and unload hooks, which are async
# callables that will be called when the plugin is loaded.

# Note: a contextvar is used here to transfer the clientsession through the plugin.

plugin_session: contextvars.ContextVar[aiohttp.ClientSession] = contextvars.ContextVar("session")


@hooks_piece.load_hook()
async def create_session() -> None:
    session = aiohttp.ClientSession()
    plugin_session.set(session)


# We make sure to close the clientsession when the plugin is unloaded...


@hooks_piece.unload_hook()
async def close_session() -> None:
    session = plugin_session.get()
    await session.close()


# Now we can use this in our commands...


@hooks_piece.slash_command()
async def make_request(inter: disnake.CommandInteraction) -> None:
    session = plugin_session.get()
    async with session.get("...") as response:
        data = await response.text()

    await inter.response.send_message(data)


setup, teardown = hooks_piece.create_extension_handlers()
