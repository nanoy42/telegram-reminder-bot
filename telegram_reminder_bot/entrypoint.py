# telegram-reminder-bot Copyright (c) 2021-2022 Yoann Piétri
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

#    __       __                                                       _           __             __          __
#   / /____  / /__  ____ __________ _____ ___     ________  ____ ___  (_)___  ____/ /__  _____   / /_  ____  / /_
#  / __/ _ \/ / _ \/ __ `/ ___/ __ `/ __ `__ \   / ___/ _ \/ __ `__ \/ / __ \/ __  / _ \/ ___/  / __ \/ __ \/ __/
# / /_/  __/ /  __/ /_/ / /  / /_/ / / / / / /  / /  /  __/ / / / / / / / / / /_/ /  __/ /     / /_/ / /_/ / /_
# \__/\___/_/\___/\__, /_/   \__,_/_/ /_/ /_/  /_/   \___/_/ /_/ /_/_/_/ /_/\__,_/\___/_/     /_.___/\____/\__/
#                /____/

import os
import logging
import argparse
import pathlib
import shutil
import sys

from telegram_reminder_bot import __version__
from telegram_reminder_bot.bot import Bot, Configuration
from telegram_reminder_bot.models import Base


def main():
    parser = argparse.ArgumentParser(
        description=f"Telegram reminder bot v{__version__}",
        prog="telegram-reminder-bot",
    )
    parser.add_argument(
        "action",
        choices=[
            "start",
            "stop",
            "restart",
            "debug",
            "init_db",
            "init_config",
        ],
    )
    parser.add_argument(
        "-c",
        "--configuration-file",
        help="Path of the configuration file. Default to /etc/telegram-reminder-bot/config.ini",
        default="/etc/telegram-reminder-bot/config.ini",
    )
    args = parser.parse_args()

    if args.action == "init_db":
        try:
            # Read configuration file
            c = Configuration(args.configuration_file)
            # Init the database
            from sqlalchemy import create_engine

            engine = create_engine(c.engine, connect_args={"check_same_thread": False})
            Base.metadata.create_all(engine)
            print("[OK] The database was successfully initialized")
        except Exception as e:
            print(f"[ERR] The database couldn't be initialized. The error was {e}")
    elif args.action == "init_config":
        # This action will copy the default configuration file to the specified location by -c
        # or --configuration-file.
        try:
            directory = pathlib.Path(__file__).parent.resolve()
            target_directory = pathlib.Path(args.configuration_file).parent
            if not target_directory.is_dir():
                print(
                    f"[WARN] Directory {target_directory} does not exists. Attempting to create it."
                )
                try:
                    target_directory.mkdir(parents=True, exist_ok=True)
                    print(f"[OK] Directory {target_directory} successfully created.")
                except Exception as e:
                    print(
                        f"[ERR] Creation of the directory {target_directory} failed : {e}"
                    )
                    sys.exit(os.EX_OSFILE)
            shutil.copyfile(directory / "config.example.ini", args.configuration_file)
            print(
                f"[OK] The default configuration file was copied to {args.configuration_file}."
            )
        except Exception as e:
            print(f"[ERR] Impossible to copy the default configuration file : {e}")
            sys.exit(os.EX_OSFILE)
    elif args.action == "debug":
        logging.basicConfig(level=logging.DEBUG)
        # Start the bot
        b = Bot(args.configuration_file)
        b.start_bot()
    else:
        c = Configuration(args.configuration_file)
        logging.basicConfig(filename=c.logs_path, level=logging.WARNING)

        from daemons.prefab import run

        class ListBotDaemon(run.RunDaemon):
            def __init__(self, configuration_path, *args, **kwargs):
                self.configuration_path = configuration_path
                super().__init__(*args, **kwargs)

            def run(self):
                b = Bot(self.configuration_path)
                b.start_bot()

        pidfile = "/tmp/telegram-reminder-bot.pid"
        configuration_path = pathlib.Path(args.configuration_file).resolve()
        d = ListBotDaemon(configuration_path, pidfile=pidfile)

        if args.action == "start":
            d.start()
        elif args.action == "stop":
            d.stop()
        elif args.action == "restart":
            d.restart()


if __name__ == "__main__":
    main()
