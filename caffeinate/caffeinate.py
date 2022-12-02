import argparse, time, re, subprocess, signal, sys
from datetime import datetime
from threading import Thread
from pynput.keyboard import Key, Controller, Listener
from typing import Union, AnyStr, Tuple
from Xlib import display

PROGNAME='caffeinate'
VERSION='0.1.0'

class cf_time:
    @classmethod
    def convert_time(cls, tm: str, *, split: bool = False) -> Union[int, Tuple[int, int, int]]:
        hours = minutes = seconds = 0

        # HH:MM:SS
        m = re.match(r'(\d{1,2}):(\d{2}):(\d{2})', tm)
        if m:
            hours, minutes, seconds = m.group(1, 2, 3)
            if split:
                return int(hours), int(minutes), int(seconds)
            hours = convert_time(hours + 'h')
            minutes = cls.convert_time(minutes + 'm')
            return hours + minutes + seconds

        # MM:SS
        m = re.match(r'(\d{1,2}):(\d{2})', tm)
        if m:
            minutes, seconds = m.group(1, 2)
            if split:
                return 0, int(minutes), int(seconds)
            minutes = cls.convert_time(minutes + 'm')
            return minutes + int(seconds)

        # [S]S[x], x = m|h|s
        m = re.match(r'([1-9][0-9]*)([mhs]?)', tm)
        if not m:
            raise ValueError(f"invalid time: '{tm}'")

        number = int(m[1])
        unit = m[2] or 's'
        multiplier = {'h': 3600, 'm': 60, 's': 1}[unit]

        if split:
            minutes = hours = 0
            seconds = number * multiplier

            # Extract minutes and hours from number of seconds
            minutes = int(seconds / 60)
            seconds %= 60
            hours = int(minutes / 60)
            minutes %= 60

            return hours, minutes, seconds

        # No split, return total number of seconds
        return number * multiplier

    def __init__(self, tm: str = ''):
        """Initialize a CLASS object."""
        self.__hours, self.__minutes, self.__seconds = self.convert_time(tm, split=True)

        # Format time string
        tm = "%d"
        fields = self.__seconds
        if self.__minutes:
            tm = "%d:%02d"
            fields = (self.__minutes, self.__seconds)
        if self.__hours:
            tm = "%d:%02d:%02d"
            fields = (self.__hours, self.__minutes, self.__seconds)
        self.__srep = tm % fields

    def __str__(self) -> str:
        return self.__srep

    def __repr__(self) -> str:
        return f"cf_time(hours={self.__hours}, minutes={self.__minutes}, seconds={self.__seconds})"

    @property
    def seconds(self) -> int:
        """The number of seconds total."""
        return self.__seconds + self.__minutes * 60 + self.__hours * 60

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

class CaffeinateRunCommand:
    def __init__(self):
        for sig in [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]:
            signal.signal(sig, self.sigaction)

    def sigaction(self, *args):
        self.release()
        sys.exit(1)

    def release(self):
        if subprocess.run(['xdg-screensaver', 'resume', self.wid]).returncode != 0:
            die("could not uninhibit desktop idleness")

    def suspend(self):
        if subprocess.run(['xdg-screensaver', 'suspend', self.wid]).returncode != 0:
            die("could not inhibit desktop idleness")

    def __make_window(self):
        self.window = make_unmapped_window(PROGNAME)
        self.wid = hex(self.window.id)

    def run(self, command: str, *args):
        self.__make_window()
        self.suspend()
        command = [command] + list(args)
        subprocess.run(command)
        self.release()

    def sleep(self, seconds: int):
        self.__make_window()
        self.suspend()
        print(f"Sleeping for {seconds} seconds")
        time.sleep(seconds)
        self.release()

def make_unmapped_window(wm_name) -> display.Display:
    screen = display.Display().screen()
    window = screen.root.create_window(0, 0, 1, 1, 0, screen.root_depth)
    window.set_wm_name(wm_name)
    window.set_wm_protocols([])
    return window

def die(err):
    sys.exit(PROGNAME + ': ' + err)

def run():
    """
    Listens for user's keystrokes, if none for given time, shift is pressed to keep the computer awake
    Args:
        --time ([int]): [default time interval for keypress to take place]
    """
    parser = argparse.ArgumentParser(prog=PROGNAME)
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
    parser_sleep.add_argument('TIME', default='1:30', type=cf_time,
                              help='sleep for a certain amoutn of time; can be number with optional h/m suffix, '
                              'or a string in the [[HH:]M]M:SS format')
    # Global options
    parser.add_argument('-V', '--version', action='version', version=f"%(prog)s {VERSION}",
                        help='print the program version and exit')
    parser.add_argument('-t', '--time', default='1:30', type=cf_time,
                        help='activate after certain time either; can be number with optional h/m suffix, '
                        'or a string in the [[HH:]M]M:SS format')
    args = parser.parse_args()

    match args.subcommand:
        case 'loop':
            caffeinate = Caffeinate()

            listener = Listener(
                on_press=caffeinate.on_press,
                on_release=caffeinate.on_release)
            awake = Thread(target=caffeinate.stay_awake, args=(args.time.seconds,))

            listener.start()
            awake.start()
            listener.join()
            awake.join()
        case 'do':
            runcmd = CaffeinateRunCommand()
            runcmd.run(args.COMMAND, *args.ARGUMENT)
        case 'sleep':
            runcmd = CaffeinateRunCommand()
            runcmd.sleep(args.TIME.seconds)

if __name__ == '__main__':
    run()
