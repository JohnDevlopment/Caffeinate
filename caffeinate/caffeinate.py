"""
A module of classes that keep the computer awake for a period of time.
"""
from __future__ import annotations

import argparse
import re
import signal
import subprocess
import sys
import time
from contextlib import AbstractContextManager
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING, Annotated, Optional, Type, no_type_check

from pynput.keyboard import Controller, Key, Listener
from typer import Argument, Exit, Option, Typer
from Xlib import display

from . import __version__ as VERSION

if TYPE_CHECKING:
    from types import TracebackType

    from typing_extensions import Self

APP = str(Path(sys.argv[0]).stem)
CONTEXT_SETTINGS = {
    'help_option_names': ["--help", "-h"],
}
app = Typer(context_settings=CONTEXT_SETTINGS)

def timestring(string: str) -> timedelta:
    if (not re.fullmatch(r'(?:[0-9]{1,2}:)*[0-9]{2}', string)):
        raise TypeError(f"invalid time string {string!r}")

    match string.split(":"):
        case (hs, ms, ss):
            return timedelta(hours=int(hs), minutes=int(ms), seconds=int(ss))
        case (ms, ss):
            return timedelta(minutes=int(ms), seconds=int(ss))
        case lst:
            if len(lst) != 1:
                raise ValueError(f"time string {string!r} has too many fields")

    return timedelta(seconds=int(lst[0]))

class Caffeinate:
    def __init__(self):
        self.hist = 0
        self.last_online = datetime.now()
        self.keyboard = Controller()

    def on_press(self, key):
        pass

    def on_release(self, key):
        if key == Key.esc:
            self.hist += 1

            # if esc pressed 3 times, exit
            if self.hist == 3:
                # Stop listener
                return False
        else:
            self.hist = 0

    def stay_awake(self, wait: int):
        print(f"Serving caffeine every {wait} seconds.")
        print("To quit, press the Escape key three times.")

        while self.hist < 3:
            if (datetime.now() - self.last_online).seconds > wait:
                self.keyboard.press(Key.shift)
                self.keyboard.release(Key.shift)
                self.last_online = datetime.now()
            time.sleep(1)

        return False

class SuspendedWindow(AbstractContextManager):
    def __init__(self, wid: str):
        self.wid = wid

    def __enter__(self) -> Self:
        self.suspend()
        return self

    def __exit__(self, exc_type: Type[BaseException] | None,
                 exc_value: BaseException | None,
                 traceback: TracebackType | None):
        self.release()

    def release(self):
        subprocess.run(['xdg-screensaver', 'resume', self.wid], text=True, check=True)

    def suspend(self):
        subprocess.run(['xdg-screensaver', 'suspend', self.wid], text=True, check=True)

class CaffeinateRunCommand:
    def __init__(self):
        for sig in [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]:
            signal.signal(sig, self._sigaction)

    def _sigaction(self, *_args):
        self.release()
        sys.exit(1)

    def release(self):
        subprocess.run(['xdg-screensaver', 'resume', self.wid], text=True, check=True)

    @no_type_check
    def __make_window(self):
        self.window = make_unmapped_window(APP)
        self.wid = hex(self.window.id)

    def run(self, command: str, *args):
        """
        Run COMMAND with *ARGS with a suspended window.
        """
        self.__make_window()
        with SuspendedWindow(self.wid):
            subprocess.run([command, *args])

    def sleep(self, seconds: int):
        """
        Sleep for SECONDS seconds with a suspended window.
        """
        self.__make_window()
        with SuspendedWindow(self.wid):
            print(f"Sleeping for {seconds} seconds")
            time.sleep(seconds)

def make_unmapped_window(wm_name) -> display.Display:
    screen = display.Display().screen()
    window = screen.root.create_window(0, 0, 1, 1, 0, screen.root_depth)
    window.set_wm_name(wm_name)
    window.set_wm_protocols([])
    return window

def die(err):
    sys.exit(APP + ': ' + err)

def parse_arguments():
    parser = argparse.ArgumentParser(prog=APP)
    subparsers = parser.add_subparsers(help='pass --help to the subcommand for options',
                                       title='subcommands', dest='subcommand', required=True)
    # Subcommand 'do'
    parser_do = subparsers.add_parser('do', help='keep the computer awake while a command runs',
                                      description='Runs COMMAND and keeps computer awake until it finishes.')
    parser_do.add_argument('COMMAND', help='command to run')
    parser_do.add_argument('ARGUMENT', nargs='*', default=None, help='arguments to command')

    # Subcommand 'loop'
    parser_loop = subparsers.add_parser('loop', help='keep the computer awake until the user stops it',
                                        description="Run this command to prevent the computer from falling asleep. "
                                        "This command never finishes until the user stops it.")
    # Subcommand 'sleep'
    parser_sleep = subparsers.add_parser('sleep', help='keep the computer awake for a given period of time',
                                         description='This command keeps the computer awake for given amount of time.')
    parser_sleep.add_argument('TIME', default='1:30', type=timestring,
                              help='sleep for a certain amoutn of time; can be number with optional h/m suffix, '
                              'or a string in the [[HH:]M]M:SS format')
    # Global options
    parser.add_argument('-V', '--version', action='version', version=f"%(prog)s {VERSION}",
                        help='print the program version and exit')
    parser.add_argument('-t', '--time', default='1:30', type=timestring,
                        help='activate after certain time either; can be number with optional h/m suffix, '
                        'or a string in the [[HH:]M]M:SS format')

    return parser.parse_args()

@app.command()
def loop(
    seconds: Annotated[float, Argument()]=3.0
):
    """
    Keep the screen awake indefinitely.

    This command does not stop on its own: press Escape three
    times to end it.
    """
    caf = Caffeinate()
    listener = Listener(
        on_press=caf.on_press,
        on_release=caf.on_release       # pyright: ignore
    )
    worker = Thread(target=caf.stay_awake, args=(seconds,))

    listener.start()
    worker.start()
    listener.join()
    worker.join()

@app.command()
def do(
    command: Annotated[str, Argument(help="The command to run.")],
    args: Annotated[Optional[list[str]], Argument(show_default=False)]=None
):
    """
    Run a command, keeping the screen awake all the while.
    """
    runcmd = CaffeinateRunCommand()
    args = args if args is not None else []
    runcmd.run(command, *args)

@app.command()
def sleep(
    time: Annotated[timedelta, Argument(help="Sleep for this amount of time.", parser=timestring,
                                        metavar="TIME", show_default=False)]
):
    """
    Sleep for a given period of time while keeping the screen
    awake.
    """
    runcmd = CaffeinateRunCommand()
    runcmd.sleep(time.seconds)

def version_callback(value: bool) -> None:
    if value:
        print(f"{APP} version {VERSION}")
        raise Exit()

@app.callback()
def run(
    _version: Annotated[Optional[bool], Option("--version", callback=version_callback,
                                               help="Show the program version and exit.",
                                               is_eager=True)]=None
):
    """
    Keep the computer awake while doing something.
    """

if __name__ == '__main__':
    app()
