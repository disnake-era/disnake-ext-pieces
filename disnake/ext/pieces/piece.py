# SPDX-License-Identifier: LGPL-3.0-only

from __future__ import annotations

import asyncio
import dataclasses
import logging
import sys
import typing as t

import disnake
from disnake.ext import commands, tasks

__all__ = ("Piece", "PieceMetadata", "get_parent_piece")

LOGGER = logging.getLogger(__name__)
_INVALID: t.Final[t.Sequence[str]] = (t.__file__, __file__)

T = t.TypeVar("T")

if sys.version_info <= (3, 9):
    import typing_extensions

    P = typing_extensions.ParamSpec("P")
    Self = typing_extensions.Self
else:
    P = t.ParamSpec("P")
    Self = t.Self

AnyBot = t.Union[
    commands.Bot,
    commands.AutoShardedBot,
    commands.InteractionBot,
    commands.AutoShardedInteractionBot,
]

BotT = t.TypeVar("BotT", bound = AnyBot)

Coro = t.Coroutine[t.Any, t.Any, T]
MaybeCoro = t.Union[Coro[T], T]
EmptyAsync = t.Callable[[], Coro[None]]
SetupFunc = t.Callable[[BotT], None]

AnyCommand = commands.Command[t.Any, t.Any, t.Any]
AnyGroup = commands.Group[t.Any, t.Any, t.Any]

CoroFunc = t.Callable[..., Coro[t.Any]]
CoroFuncT = t.TypeVar("CoroFuncT", bound = CoroFunc)
CoroDecorator = t.Callable[[CoroFunc], T]

LocalizedOptional = t.Union[t.Optional[str], disnake.Localized[t.Optional[str]]]
PermissionsOptional = t.Optional[t.Union[disnake.Permissions, int]]

LoopT = t.TypeVar("LoopT", bound = "tasks.Loop[t.Any]")

PrefixCommandCheck = t.Callable[[commands.Context[t.Any]], MaybeCoro[bool]]
AppCommandCheck = t.Callable[[disnake.CommandInteraction], MaybeCoro[bool]]

PrefixCommandCheckT = t.TypeVar("PrefixCommandCheckT", bound = PrefixCommandCheck)
AppCommandCheckT = t.TypeVar("AppCommandCheckT", bound = AppCommandCheck)


class CheckAware(t.Protocol):
    checks: t.List[t.Callable[..., MaybeCoro[bool]]]


@dataclasses.dataclass
class PieceMetadata:
    """Represents metadata for a :class:`Piece`.

    Parameters
    ----------
    name: :class:`str`
        Plugin's name.
    extras: Dict[:class:`str`, :class:`str`]
        A dict of extra metadata for a plugin.

        .. versionadded:: 0.2.4
    """

    name: str
    """Piece's name"""
    extras: t.Dict[str, t.Any]
    """A dict of extra metadata for a piece."""


class ExtrasAware(t.Protocol):
    extras: t.Dict[str, t.Any]


def get_parent_piece(obj: ExtrasAware) -> Piece[AnyBot]:
    """Get the plugin to which the provided object is registered.

    This only works with objects that support an ``extras`` attribute.

    Parameters
    ----------
    obj: ExtrasAware
        Any object that supports an ``extras`` attribute, which should be a dict
        with ``str`` keys.

    Returns
    -------
    Piece:
        The piece to which the object is registered.

    Raises
    ------
    LookupError:
        The object is not registered to any piece.
    """
    if plugin := obj.extras.get("piece"):
        return plugin

    raise LookupError(f"Object {type(obj).__name__!r} does not belong to a Piece.")


def _get_source_module_name() -> str:
    # Get current frame from exception traceback...
    try:
        raise Exception  # noqa: TRY002, TRY301
    except Exception as exc:
        tb = exc.__traceback__

    if not tb:
        # No traceback, therefore can't access frames and infer plugin name...
        LOGGER.warning("Failed to infer file name, defaulting to 'piece'.")
        return "piece"

    # Navigate all frames for one with a valid path.
    # Note that we explicitly filter out:
    # - the stdlib typing module; if the generic parameter is specified, this
    #   will be encountered before the target module.
    # - this file; we don't want to just return "plugin" if possible.
    frame = tb.tb_frame
    while frame := frame.f_back:
        if frame.f_code.co_filename not in _INVALID:
            break

    else:
        LOGGER.warning("Failed to infer file name, defaulting to 'piece'.")
        return "piece"

    module_name = frame.f_locals["__name__"]
    LOGGER.debug("Module name resolved to %r", module_name)
    return module_name


class Piece(t.Generic[BotT]):
    """An extension manager similar to disnake's :class:`commands.Cog`.

    A piece can hold commands and listeners, and supports being loaded through
    `bot.load_extension()` as per usual, and can similarly be unloaded and
    reloaded.

    Pieces can be constructed via :meth:`.with_metadata` to provide extra
    information to the piece.

    Parameters
    ----------
    name: Optional[:class:`str`]
        The name of the piece. Defaults to the module the piece is created in.
    logger: Optional[Union[:class:`logging.Logger`, :class:`str`]]
        The logger or its name to use when logging piece events.
        If not specified, defaults to `disnake.ext.pieces.piece`.
    **extras: Dict[:class:`str`, Any]
        A dict of extra metadata for this piece.
    """

    __slots__ = (
        "metadata",
        "logger",
        "_bot",
        "_commands",
        "_slash_commands",
        "_message_commands",
        "_user_commands",
        "_command_checks",
        "_slash_command_checks",
        "_message_command_checks",
        "_user_command_checks",
        "_listeners",
        "_loops",
        "_pre_load_hooks",
        "_post_load_hooks",
        "_pre_unload_hooks",
        "_post_unload_hooks",
        "_global_command_checks",
        "_global_command_once_checks",
        "_global_application_command_checks",
        "_global_slash_command_checks",
        "_global_message_command_checks",
        "_global_user_command_checks",
    )

    metadata: PieceMetadata
    """The metadata assigned to the piece."""

    logger: logging.Logger
    """The logger associated with this piece."""

    def __init__(
        self: Self,
        *,
        name: t.Optional[str] = None,
        logger: t.Union[logging.Logger, str, None] = None,
        **extras: t.Any,
    ) -> None:
        self.metadata: PieceMetadata = PieceMetadata(
            name = name or _get_source_module_name(),
            extras = extras,
        )

        if logger is not None:
            if isinstance(logger, str):
                logger = logging.getLogger(logger)

        else:
            logger = LOGGER

        self.logger = logger

        self._commands: t.Dict[
            str,
            commands.Command["Piece[BotT]", t.Any, t.Any],  # type: ignore
        ] = {}
        self._message_commands: t.Dict[str, commands.InvokableMessageCommand] = {}
        self._slash_commands: t.Dict[str, commands.InvokableSlashCommand] = {}
        self._user_commands: t.Dict[str, commands.InvokableUserCommand] = {}

        self._command_checks: t.MutableSequence[PrefixCommandCheck] = []
        self._slash_command_checks: t.MutableSequence[AppCommandCheck] = []
        self._message_command_checks: t.MutableSequence[AppCommandCheck] = []
        self._user_command_checks: t.MutableSequence[AppCommandCheck] = []

        self._global_command_checks: t.MutableSequence[PrefixCommandCheck] = []
        self._global_application_command_checks: t.MutableSequence[AppCommandCheck] = []
        self._global_slash_command_checks: t.MutableSequence[AppCommandCheck] = []
        self._global_message_command_checks: t.MutableSequence[AppCommandCheck] = []
        self._global_user_command_checks: t.MutableSequence[AppCommandCheck] = []

        self._listeners: t.Dict[str, t.MutableSequence[CoroFunc]] = {}
        self._loops: t.List[tasks.Loop[t.Any]] = []

        # These are mainly here to easily run async code at (un)load time
        # while we wait for disnake's async refactor. These will probably be
        # left in for lower disnake versions, though they may be removed someday.

        self._pre_load_hooks: t.MutableSequence[EmptyAsync] = []
        self._post_load_hooks: t.MutableSequence[EmptyAsync] = []
        self._pre_unload_hooks: t.MutableSequence[EmptyAsync] = []
        self._post_unload_hooks: t.MutableSequence[EmptyAsync] = []

        self._bot: t.Optional[BotT] = None

    @classmethod
    def with_metadata(cls: t.Type[Self], metadata: PieceMetadata) -> "Piece[t.Any]":
        """Create a Piece with pre-existing metadata.

        Parameters
        ----------
        metadata: Optional[:class:`PieceMetadata`]
            The metadata to supply to the piece.

        Returns
        -------
        :class:`Piece`
            The newly created piece. In a child class, this would instead
            return an instance of that child class.
        """
        self = cls()
        self.metadata = metadata
        return self

    @property
    def bot(self: Self) -> BotT:
        """The bot on which this piece is registered.

        This will only be available after calling :meth:`.load`.
        """
        if not self._bot:
            raise RuntimeError("Cannot access the bot on a piece that has not yet been loaded.")
        return self._bot

    @property
    def name(self: Self) -> str:
        """The name of this piece."""
        return self.metadata.name

    @property
    def extras(self: Self) -> t.Dict[str, t.Any]:
        """A dict of extra metadata for this piece.

        .. versionadded:: 0.2.4
        """
        return self.metadata.extras

    @extras.setter
    def extras(self: Self, value: t.Dict[str, t.Any]) -> None:
        self.metadata.extras = value

    @property
    def commands(
        self: Self,
    ) -> t.Sequence[commands.Command["Piece[BotT]", t.Any, t.Any]]:  # type: ignore
        """All prefix commands registered in this piece."""
        return tuple(self._commands.values())

    @property
    def slash_commands(self: Self) -> t.Sequence[commands.InvokableSlashCommand]:
        """All slash commands registered in this piece."""
        return tuple(self._slash_commands.values())

    @property
    def user_commands(self: Self) -> t.Sequence[commands.InvokableUserCommand]:
        """All user commands registered in this piece."""
        return tuple(self._user_commands.values())

    @property
    def message_commands(self: Self) -> t.Sequence[commands.InvokableMessageCommand]:
        """All message commands registered in this piece."""
        return tuple(self._message_commands.values())

    @property
    def loops(self: Self) -> t.Sequence[tasks.Loop[t.Any]]:
        return tuple(self._loops)

    def _apply_attrs(
        self: Self,
        attrs: t.Mapping[str, t.Any],
        **kwargs: t.Any,
    ) -> t.Dict[str, t.Any]:
        new_attrs = { **attrs, **{ k: v for k, v in kwargs.items() if v is not None } }

        # Ensure keys are set, but don't override any in case they are already in use.
        extras = new_attrs.setdefault("extras", {})
        extras.setdefault("piece", self)
        extras.setdefault("metadata", self.metadata)  # Backward compatibility, may remove later.

        return new_attrs

    # Prefix commands

    def command(
        self: Self,
        name: t.Optional[str] = None,
        *,
        cls: t.Optional[t.Type[commands.Command[t.Any, t.Any, t.Any]]] = None,
        **kwargs: t.Any,
    ) -> CoroDecorator[AnyCommand]:
        """See :func:`disnake.ext.commands.command`."""
        attributes: t.Dict[str, t.Any] = {}

        if cls is None:
            cls = t.cast(t.Type[AnyCommand], attributes.pop("cls", AnyCommand))

        def decorator(callback: t.Callable[..., Coro[t.Any]]) -> AnyCommand:
            if not asyncio.iscoroutinefunction(callback):
                raise TypeError(f"<{callback.__qualname__}> must be a coroutine function.")

            command = cls(callback, name = name or callback.__name__, **attributes)
            self._commands[command.qualified_name] = command

            return command

        return decorator

    def group(
        self: Self,
        name: t.Optional[str] = None,
        *,
        cls: t.Optional[t.Type[commands.Group[t.Any, t.Any, t.Any]]] = None,
        **kwargs: t.Any,
    ) -> CoroDecorator[AnyGroup]:
        """See :func:`disnake.ext.commands.group`."""
        attributes: t.Dict[str, t.Any] = {}

        if cls is None:
            cls = t.cast(t.Type[AnyGroup], attributes.pop("cls", AnyGroup))

        def decorator(callback: t.Callable[..., Coro[t.Any]]) -> AnyGroup:
            if not asyncio.iscoroutinefunction(callback):
                raise TypeError(f"<{callback.__qualname__}> must be a coroutine function.")

            command = cls(callback, name = name or callback.__name__, **attributes)
            self._commands[command.qualified_name] = command

            return command

        return decorator

    # Application commands

    def slash_command(
        self: Self,
        *,
        name: LocalizedOptional = None,
        **attributes: t.Any,
    ) -> CoroDecorator[commands.InvokableSlashCommand]:
        """See :func:`disnake.ext.commands.slash_command`."""

        def decorator(callback: t.Callable[..., Coro[t.Any]]) -> commands.InvokableSlashCommand:
            if not asyncio.iscoroutinefunction(callback):
                raise TypeError(f"<{callback.__qualname__}> must be a coroutine function")

            command = commands.InvokableSlashCommand(
                callback,
                name = name or callback.__name__,
                **attributes,
            )
            self._slash_commands[command.qualified_name] = command

            return command

        return decorator

    def user_command(
        self: Self,
        *,
        name: LocalizedOptional = None,
        **attributes: t.Any,
    ) -> CoroDecorator[commands.InvokableUserCommand]:
        """See :func:`disnake.ext.commands.user_command`."""

        def decorator(callback: t.Callable[..., Coro[t.Any]]) -> commands.InvokableUserCommand:
            if not asyncio.iscoroutinefunction(callback):
                raise TypeError(f"<{callback.__qualname__}> must be a coroutine function")

            command = commands.InvokableUserCommand(
                callback,
                name = name or callback.__name__,
                **attributes,
            )
            self._user_commands[command.qualified_name] = command

            return command

        return decorator

    def message_command(
        self: Self,
        *,
        name: LocalizedOptional = None,
        **attributes: t.Any,
    ) -> CoroDecorator[commands.InvokableMessageCommand]:
        """See :func:`disnake.ext.commands.message_command`."""

        def decorator(callback: t.Callable[..., Coro[t.Any]]) -> commands.InvokableMessageCommand:
            if not asyncio.iscoroutinefunction(callback):
                raise TypeError(f"<{callback.__qualname__}> must be a coroutine function")

            command = commands.InvokableMessageCommand(
                callback,
                name = name or callback.__name__,
                **attributes,
            )
            self._message_commands[command.qualified_name] = command

            return command

        return decorator

    # Checks

    # NOTE: The decision to implement them only partially arises from two issues:
    # my laziness and the fact that disnake's "official" Bot api does not allow
    # complete fine-tuning either. As such, current API mirrors that of disnake's
    # one. A bit of additional info can be found in global_application_command_check
    # docstring.

    def command_check(self: Self, predicate: PrefixCommandCheckT) -> PrefixCommandCheckT:
        """Add a check to all prefix commands in this plugin."""
        self._command_checks.append(predicate)
        return predicate

    def slash_command_check(self: Self, predicate: AppCommandCheckT) -> AppCommandCheckT:
        """Add a check to all slash commands in this plugin."""
        self._slash_command_checks.append(predicate)
        return predicate

    def message_command_check(self: Self, predicate: AppCommandCheckT) -> AppCommandCheckT:
        """Add a check to all message commands in this plugin."""
        self._message_command_checks.append(predicate)
        return predicate

    def user_command_check(self: Self, predicate: AppCommandCheckT) -> AppCommandCheckT:
        """Add a check to all user commands in this plugin."""
        self._user_command_checks.append(predicate)
        return predicate

    def global_command_check(self: Self, predicate: PrefixCommandCheckT) -> PrefixCommandCheckT:
        """Add a global prefix command check."""
        self._global_command_checks.append(predicate)
        return predicate

    def global_command_check_once(
        self: Self,
        predicate: PrefixCommandCheckT,
    ) -> PrefixCommandCheckT:
        """Add a global prefix command 'once' check."""
        self._global_command_once_checks.append(predicate)
        return predicate

    def global_application_command_check(
        self: Self,
        predicate: AppCommandCheckT,
    ) -> AppCommandCheckT:
        """Add a global application command check.

        Note that unlike regular
        :meth:`disnake.ext.commands.InteractionBot.application_command_check`
        this decorator does not allow customization and instead registers
        this check to run on any application command type automatically.

        If you still desire support for fine-tuning params, open an issue.
        """
        self._global_application_command_checks.append(predicate)
        return predicate

    def global_slash_command_check(self: Self, predicate: AppCommandCheckT) -> AppCommandCheckT:
        """Add a global slash command check."""
        self._global_slash_command_checks.append(predicate)
        return predicate

    def global_message_command_check(self: Self, predicate: AppCommandCheckT) -> AppCommandCheckT:
        """Add a global message command check."""
        self._global_message_command_checks.append(predicate)
        return predicate

    def global_user_command_check(self: Self, predicate: AppCommandCheckT) -> AppCommandCheckT:
        """Add a global user command check."""
        self._global_user_command_checks.append(predicate)
        return predicate

    # Listeners

    def add_listeners(self: Self, *callbacks: CoroFunc, event: t.Optional[str] = None) -> None:
        """Add multiple listeners to the piece.

        Parameters
        ----------
        *callbacks: CoroFunc
            Listener callbacks.
        event: :class:`str`
            The name of a single event to register all callbacks under. If not provided,
            the callbacks will be registered individually based on function's name.
        """
        for callback in callbacks:
            key = callback.__name__ if event is None else event
            self._listeners.setdefault(key, []).append(callback)

    def listener(self: Self, event: t.Optional[str] = None) -> t.Callable[[CoroFuncT], CoroFuncT]:
        """Mark a function as a listener.

        This is the piece equivalent of :meth:`commands.Bot.listen`.

        Parameters
        ----------
        event: :class:`str`
            The name of the event being listened to. If not provided, it
            defaults to the function's name.
        """

        def decorator(callback: CoroFuncT) -> CoroFuncT:
            self.add_listeners(callback, event = event)
            return callback

        return decorator

    # Tasks

    def register_loop(self: Self, *, wait_until_ready: bool = False) -> t.Callable[[LoopT], LoopT]:
        """Register loop to start/stop on piece load/unload.

        Parameters
        ----------
        wait_until_ready: :class:`bool`
            Whether or not to add a simple `loop.before_loop` callback that waits
            until the bot is ready. This can be handy if you load pieces before
            you start the bot (which you should!) and make api requests with a
            loop.
            .. warn::
                This only works if the loop does not already have a `before_loop`
                callback registered.
        """

        def decorator(loop: LoopT) -> LoopT:
            if wait_until_ready:
                if loop._before_loop is not None:  # type: ignore
                    raise TypeError("This loop already has a `before_loop` callback registered.")

                async def _before_loop() ->...:
                    await self.bot.wait_until_ready()

                loop.before_loop(_before_loop)

            self._loops.append(loop)
            return loop

        return decorator

    def loop(self: Self,
             *,
             wait_until_ready: bool = True,
             **loop_args: t.Any) -> t.Callable[[CoroFuncT], tasks.Loop[CoroFuncT]]:
        """Shortcut decorator for :func:`disnake.ext.tasks.loop` + :meth:`Piece.register_loop`.

        Parameters
        ----------
        wait_until_ready: :class:`bool`
            Whether or not to add a simple `loop.before_loop` callback that waits
            until the bot is ready. This can be handy if you load pieces before
            you start the bot (which you should!) and make api requests with a
            loop.
            .. warn::
                This only works if the loop does not already have a `before_loop`
                callback registered.
        **loop_args:
            Keyword arguments to pass to :func:`disnake.ext.tasks.loop`.
        """

        def decorator(coro: CoroFuncT) -> tasks.Loop[CoroFuncT]:
            f = tasks.loop(**loop_args)(coro)
            self.register_loop(wait_until_ready = wait_until_ready)(f)
            return f

        return decorator

    # Plugin (un)loading...

    @staticmethod
    def _prepend_plugin_checks(
        checks: t.Sequence[t.Union[PrefixCommandCheck, AppCommandCheck]],
        command: CheckAware,
    ) -> None:
        """Update command checks with piece-wide checks.

        To remain consistent with the behaviour of e.g. commands.Cog.cog_check,
        piece-wide checks are **prepended** to the commands' local checks.
        """
        if checks:
            command.checks = [*checks, *command.checks]

    # In the following case of loading global checks we use the decorator
    # interfaces instead of functional ones because internally disnake uses
    # the type ignore directive (for another reason) and as such likely
    # doesn't notice any issues. See also: disnake#1045

    async def load(self: Self, bot: BotT) -> None:
        """Register commands, checks, etc. to the bot and run pre- and post-load hooks.

        Parameters
        ----------
        bot: BotT
            The bot on which to register the piece's commands.
        """
        self._bot = bot

        await asyncio.gather(*(hook() for hook in self._pre_load_hooks))

        if isinstance(bot, commands.BotBase):
            for command in self._commands.values():
                bot.add_command(command)  # type: ignore
                self._prepend_plugin_checks(self._command_checks, command)

            for check in self._global_command_checks:
                bot.add_check(check)

            for check in self._global_command_once_checks:
                bot.add_check(check, call_once = True)

        for check in self._global_application_command_checks:
            bot.application_command_check(
                slash_commands = True,
                user_commands = True,
                message_commands = True,
            )(check)

        for command in self._slash_commands.values():
            bot.add_slash_command(command)
            self._prepend_plugin_checks(self._slash_command_checks, command)

        for check in self._global_slash_command_checks:
            bot.application_command_check(slash_commands = True)(check)

        for command in self._user_commands.values():
            bot.add_user_command(command)
            self._prepend_plugin_checks(self._user_command_checks, command)

        for check in self._global_user_command_checks:
            bot.application_command_check(user_commands = True)(check)

        for command in self._message_commands.values():
            bot.add_message_command(command)
            self._prepend_plugin_checks(self._message_command_checks, command)

        for check in self._global_message_command_checks:
            bot.application_command_check(message_commands = True)(check)

        for event, listeners in self._listeners.items():
            for listener in listeners:
                bot.add_listener(listener, event)

        for loop in self._loops:
            loop.start()

        await asyncio.gather(*(hook() for hook in self._post_load_hooks))

        bot._schedule_delayed_command_sync()  # type: ignore

        self.logger.info(f"Successfully loaded piece `{self.metadata.name}`")

    # As there's no decorator interface for removing checks (obviously) we are
    # unfortunately forced to use the type: ignore. See also: disnake#1045

    async def unload(self: Self, bot: BotT) -> None:
        """Remove commands, checks, etc. from the bot and run pre- and post-unload hooks.

        Parameters
        ----------
        bot: BotT
            The bot from which to unload the piece's commands.
        """
        await asyncio.gather(*(hook() for hook in self._pre_unload_hooks))

        if isinstance(bot, commands.BotBase):
            for command in self._commands:
                bot.remove_command(command)

            for check in self._global_command_checks:
                bot.remove_check(check)

            for check in self._global_command_once_checks:
                bot.remove_check(check, call_once = True)

        for check in self._global_application_command_checks:
            bot.remove_app_command_check(
                check,  # type: ignore
                slash_commands = True,
                user_commands = True,
                message_commands = True,
            )

        for command in self._slash_commands:
            bot.remove_slash_command(command)

        for check in self._global_slash_command_checks:
            bot.remove_app_command_check(check, slash_commands = True)  # type: ignore

        for command in self._user_commands:
            bot.remove_user_command(command)

        for check in self._global_user_command_checks:
            bot.remove_app_command_check(check, user_commands = True)  # type: ignore

        for command in self._message_commands:
            bot.remove_message_command(command)

        for check in self._global_message_command_checks:
            bot.remove_app_command_check(check, message_commands = True)  # type: ignore

        for event, listeners in self._listeners.items():
            for listener in listeners:
                bot.remove_listener(listener, event)

        for loop in self._loops:
            loop.cancel()

        await asyncio.gather(*(hook() for hook in self._post_unload_hooks))

        bot._schedule_delayed_command_sync()  # type: ignore

        self.logger.info(f"Successfully unloaded piece `{self.metadata.name}`")

    def load_hook(self: Self, post: bool = False) -> t.Callable[[EmptyAsync], EmptyAsync]:
        """Mark a function as a load hook.

        Parameters
        ----------
        post: :class:`bool`
            Whether the hook is a post-load or pre-load hook.
        """
        hooks = self._post_load_hooks if post else self._pre_load_hooks

        def wrapper(callback: EmptyAsync) -> EmptyAsync:
            hooks.append(callback)
            return callback

        return wrapper

    def unload_hook(self: Self, post: bool = False) -> t.Callable[[EmptyAsync], EmptyAsync]:
        """Mark a function as an unload hook.

        Parameters
        ----------
        post: :class:`bool`
            Whether the hook is a post-unload or pre-unload hook.
        """
        hooks = self._post_unload_hooks if post else self._pre_unload_hooks

        def wrapper(callback: EmptyAsync) -> EmptyAsync:
            hooks.append(callback)
            return callback

        return wrapper

    def create_extension_handlers(self: Self) -> t.Tuple[SetupFunc[BotT], SetupFunc[BotT]]:
        """Create basic setup and teardown handlers for an extension.

        Simply put, these functions ensure :meth:`.load` and :meth:`.unload`
        are called when the piece is loaded or unloaded, respectively.
        """

        def setup(bot: BotT) -> None:
            _ = asyncio.create_task(self.load(bot))

        def teardown(bot: BotT) -> None:
            _ = asyncio.create_task(self.unload(bot))

        return setup, teardown
