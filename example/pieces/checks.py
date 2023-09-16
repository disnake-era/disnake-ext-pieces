# SPDX-License-Identifier: LGPL-3.0-only

import disnake
from disnake.ext import commands, pieces

Context = commands.Context[commands.Bot]

# Create a basic plugin...

checks_piece: pieces.Piece[commands.Bot] = pieces.Piece()


# First, we define a local check...
async def local_check(ctx: Context) -> bool:
    # Check if the message was sent in a channel with "foo" in its name...
    print("B")
    if isinstance(ctx.channel, disnake.DMChannel):
        return False

    return "foo" in ctx.channel.name.lower()


# Now, we add a check that applies to all prefix commands defined in this
# plugin. This is done using the `@plugin.command_check`-decorator. The same
# can be done for application commands using the `@plugin.slash_command_check`,
# `@plugin.message_command_check`, or `@plugin.user_command_check` for their
# respective command types.


@checks_piece.command_check
async def global_check_whoa(ctx: Context) -> bool:
    # Check if the command author is the owner...
    print("A")
    return ctx.author.id == ctx.bot.owner_id


@commands.check(local_check)  # Don't forget to add the local check!
@checks_piece.command()
async def command_with_checks(ctx: Context) -> None:
    print("C")
    await ctx.send("did the check thing!")


# Plugin-wide checks will run first, local checks afterwards. Besides that,
# checks run in the order they are defined/added to the command.

# In this case, a successful invocation of the command will print
# A
# B
# C

setup, teardown = checks_piece.create_extension_handlers()
