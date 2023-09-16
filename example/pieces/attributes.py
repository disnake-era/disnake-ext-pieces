# SPDX-License-Identifier: LGPL-3.0-only

import disnake
from disnake.ext import commands, pieces

# Parameters specified inside the plugin metadata's `command_attrs`,
# `message_command_attrs`, `slash_command_attrs`, and `user_command_attrs`
# will automatically be provided to the decorators of prefix commands,
# message commands, slash commands and user commands, respectively.

piece: pieces.Piece[commands.Bot] = pieces.Piece(slash_command_attrs = { "guild_ids": [1234] })

# This slash command will automatically receive the `guild_ids = [1234]`
# defined inside the plugin's metadata.


@piece.slash_command()
async def my_command(inter: disnake.CommandInteraction) ->...:
    ...


# This slash command overwrites the guild_ids provided by the metadata.
# It will not be available inside the guild with id 1234, but instead
# only inside the guild with id 5678.


@piece.slash_command(guild_ids = [5678])
async def my_other_command(inter: disnake.CommandInteraction) ->...:
    ...


setup, teardown = piece.create_extension_handlers()
