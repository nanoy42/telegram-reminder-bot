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

import configparser
from datetime import datetime
import logging
import sys
import signal
import re

from croniter import croniter
import telegram
from telegram.ext import CommandHandler, Updater
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from telegram_reminder_bot.models import Reminder


def signal_handler(sig, frame):
    print("You pressed Ctrl+C!")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

DATETIME_FORMAT = "%d/%m/%y %H:%M:%S"


class Configuration:
    """
    The configuration class for telegram-reminder-bot.

    Args:
        path (string): path of the configuration file.
    """

    ALLOWED_USER_NONE = 0
    ALLOWED_USER_ALL = 1
    ALLOWED_USER_SOME = 2

    def __init__(self, path):
        """Init the configuration.

        Args:
            path (string): path of the configuration file.
        """
        config = configparser.ConfigParser(
            {"token": "", "allowed_users": "", "engine": "", "path": ""}
        )
        try:
            config.read(path)
        except Exception as e:
            logging.error(f"Unable to read config : {e}")
            sys.exit()

        self.token = config.get("telegram", "token")
        self.engine = config.get("db", "engine")

        self.logs_path = config.get("logs", "path")

        allowed_users_raw = config.get("telegram", "allowed_users")
        if allowed_users_raw == "":
            self.user_policy = self.ALLOWED_USER_NONE
            self.allowed_users = []
        else:
            try:
                self.allowed_users = [int(x) for x in allowed_users_raw.split(",")]
                if 0 in self.allowed_users:
                    self.user_policy = self.ALLOWED_USER_ALL
                else:
                    self.user_policy = self.ALLOWED_USER_SOME
            except:
                logging.warning(
                    "Unable to parse the allowed users. Falling back on no user allowed."
                )
                self.user_policy = self.ALLOWED_USER_NONE
                self.allowed_users = []

    def __str__(self):
        return f"Token : {self.token}\nUser policy : {self.user_policy}\nAllowed users : {self.allowed_users}"


class Bot:
    """
    This is the class representing the bot.

    It has all the functions associated to the bot commands,
    and the mechanism to send the reminders.

    On initialization, the instance will load the configuration,
    get the database and grab telegram bot, Any failure in these
    steps is critical and will prevent the bot from working.

    When the ``start_bot`` command is called, it will equalize the reminders
    (please the Reminder class documentation) and enter an endless loop.
    In this loop, it will check the due reminders and send message if needed,
    and then listen for updates for 60 seconds. If an update is received, then
    it  is treated. After the 60 secondes, we end the listening and go back to
    the beginning of the loop.

    The loop may be interrupted using a SIGINT (Ctrl-C for instance).

    Args:
        configuration_path (string): path of the configuration file.
    """

    DOCUMENTATION = """
Possible commands : 
/start - Welcome message
/help - Help center
/addjob cron;message[;start_date] - Add a job
/showjobs - Show my jobs
/pausejob jobid - Pause the job with id jobid
/resumejob jobid - Resume the job with id jobid
/deletejob jobid - Delete the job with id jobid

In /addjob, the start_date is optional.
The possible cron values are @specific (reminder at the start date), @minutely, @hourly, @daily, @weekly, @monthly, @yearly, @annually and any valid cron expression. 
    """

    def __init__(self, configuration_path):
        """Init the bot.

        Args:
            configuration_path (string): path of the configuration file.
        """
        self.path = configuration_path
        self._load_config()
        self._get_db()
        self._get_telegram_bot()

    def _load_config(self):
        """Load configuration using the :class:`~telegram_reminder_bot.bot.Configuration` class."""
        self.config = Configuration(self.path)

        logging.info("Configuration loaded")

    def _get_db(self):
        """
        Get the database using the value in the configuration and open a session.
        """
        logging.info("Getting the database")
        engine = create_engine(
            self.config.engine, connect_args={"check_same_thread": False}
        )

        Session = sessionmaker(bind=engine)
        self.session = Session()

    def _get_telegram_bot(self):
        """
        Grab the telegram bot using the token in the configuration.

        This function also defines all the handlers and associated functions.
        """
        logging.info("Getting telegram bot")
        try:
            self.updater = Updater(token=self.config.token, use_context=True)
            logging.info("Bot {} grabbed.".format(self.updater.bot.username))
        except Exception as e:
            logging.error(f"Unable to grab bot : {e}")
            sys.exit()

        # Define handler and add them to the dispatcher
        self.dispatcher = self.updater.dispatcher

        start_handler = CommandHandler("start", self._command_start)
        help_handler = CommandHandler("help", self._command_help)
        addjob_handler = CommandHandler("addjob", self._command_addjob)
        showjobs_handler = CommandHandler("showjobs", self._command_showjobs)
        pausejob_handler = CommandHandler("pausejob", self._command_pausejob)
        resumejob_handler = CommandHandler("resumejob", self._command_resumejob)
        deletejob_handler = CommandHandler("deletejob", self._command_deletejob)

        self.dispatcher.add_handler(start_handler)
        self.dispatcher.add_handler(help_handler)
        self.dispatcher.add_handler(addjob_handler)
        self.dispatcher.add_handler(showjobs_handler)
        self.dispatcher.add_handler(pausejob_handler)
        self.dispatcher.add_handler(resumejob_handler)
        self.dispatcher.add_handler(deletejob_handler)

    def _equalize(self):
        """Equalize the reminders.

        See the :class:`~telegram_reminder_bot.models.Reminder` documentation.
        """
        logging.info("Equalizing")
        Reminder.equalize(self.session)

    def _check_reminders(self):
        """
        Check the reminders.

        This function will call the :func:`~telegram_reminder_bot.models.Reminder.get_all_due_reminders`
        to get all the reminders that are due. Then, the function will iterate over all reminders, and
        for each one of them, send a message and class the :func:`~telegram_reminder_bot.models.Reminder.update_remind`
        function to update the remind.
        """
        logging.info("Checking reminders and send message if needed")
        for reminder in Reminder.get_all_due_reminders(self.session):
            # Check if user is still authorized
            if (
                reminder.user in self.config.allowed_users
                or self.config.user_policy == self.config.ALLOWED_USER_ALL
            ):
                # If so, we send the message
                self._send_message(reminder.user, reminder.message)

                # Update the remind
                reminder.update_remind(self.session)
            else:
                logging.warning(
                    f"Reminder with unauthorized user found. Reminder id : {reminder.id}"
                )

    def _send_message(self, target_id, message, **kwargs):
        """Send a message.
        This is a small shortcut that gets the bot from the
        updater and use it to send a message.

        Args:
            target_id (int): id of the target (chat or user)
            message (string): message to send
        """
        logging.info(f"Sending message to {target_id}")
        bot = self.updater.bot
        bot.send_message(chat_id=target_id, text=message, **kwargs)

    def start_bot(self):
        """Public method to actually start the bot.

        As described in the class description, the bot will first equalize,
        the reminder using :func:`~telegram_reminder_bot.bot.Bot._equalize` and
        then enter in an endless loop, first calling :func:`~telegram_reminder_bot.bot.Bot._check_reminders`
        and then polling for updates for 60 seconds.
        """
        logging.info("Starting bot")

        self._equalize()

        logging.info("Starting loop")
        while True:
            self._check_reminders()

            # Let's set up an alarm in 60 seconds
            # This will stop the idle, as it is
            # listening for signal.SIGALRM
            logging.info("Alarm configured in 60 seconds")
            signal.alarm(60)

            logging.info("Start polling")
            self.updater.start_polling()
            self.updater.idle(stop_signals=(signal.SIGALRM,))

            logging.info("Stop polling")
            self.updater.stop()

    # Commands

    def _command_start(self, update, context):
        """This function will respond to the ``/start`` command.

        This will check if the user is allowed to use the bot. If he is, this displays
        a welcome message. If he is not, this displays that the user is not allowed
        and recommend to see more information on the ``/help`` command.

        Args:
            update (telegram.Update): update associated with the command.
            context (object): context associated with the command.
        """
        chat_id = update.effective_chat.id
        if (
            chat_id in self.config.allowed_users
            or self.config.user_policy == self.config.ALLOWED_USER_ALL
        ):
            context.bot.send_message(
                chat_id=chat_id,
                text="Welcome to reminderBot. I am a bot to send reminders. Please see the documentation with the /help command",
            )
        else:
            context.bot.send_message(
                chat_id=chat_id,
                text=f"You are not authorized to use this bot. Please see /help for more details",
            )

    def _command_help(self, update, context):
        """This function will respond to the ``/help`` command.

        This will check if the user is allowed to use the bot. If he is, this displays
        the documentation. If he is not, this displays that the user is not allowed
        and recommend to add their id to the configuration file.

        Args:
            update (telegram.Update): update associated with the command.
            context (object): context associated with the command.
        """
        chat_id = update.effective_chat.id
        if (
            chat_id in self.config.allowed_users
            or self.config.user_policy == self.config.ALLOWED_USER_ALL
        ):
            self._send_message(chat_id, self.DOCUMENTATION)
        else:
            self._send_message(
                chat_id,
                f"You are not authorized to use this bot. Please consider adding your id to the authorized list : {chat_id} (or asking for it)",
            )

    def _command_addjob(self, update, context):
        """This function will respond to the ``/addjob`` command.

        This will check if the user is allowed to use the bot. If he is,
        this will try to parse the command according to
        /addjob cron;message[;start_date]
        or
        /addjob@botusername cron;message[;start_date]
        with the start_date being optional.

        If the cron is valid (or @minutely or @specific), then this is added
        to the database.

        Args:
            update (telegram.Update): update associated with the command.
            context (object): context associated with the command.
        """
        chat_id = update.effective_chat.id
        if (
            chat_id in self.config.allowed_users
            or self.config.user_policy == self.config.ALLOWED_USER_ALL
        ):
            command = update["message"]["text"]

            # Count the number of ; in the command
            # If one ; we have the cron and the message
            # If two ; we have the cron, message and start_date
            # If anything else the message commands makes no sense

            n = command.count(";")

            if n == 1:
                regex = r"^\/addjob\S* (.*);(.*)$"
            elif n == 2:
                regex = r"^\/addjob\S* (.*);(.*);(.*)$"
            else:
                regex = r"^$"

            # Identify the cron, the message and the optional start date
            result = re.search(regex, command)

            if result:
                cron = result.group(1).lower()
                message = result.group(2)
                if n == 2:
                    try:
                        start_date = datetime.strptime(result.group(3), DATETIME_FORMAT)
                    except ValueError:
                        logging.info("Date couldn't be parsed. Using datetime.now()")
                        start_date = datetime.now()
                else:
                    start_date = datetime.now()

                # @mintutely doesn't exist in croniter
                if cron == "@minutely":
                    cron = "* * * * *"

                if cron == "@specific" or croniter.is_valid(cron):
                    # If this is not a specific job, get to the nearest "good value"
                    # of the job to have the message twice at the beginning
                    # (for instance with * * * * *) starting at 16:34:40, the
                    # next iter is at 16:35:00, 20 seconds later, and then it will go
                    # with the minute
                    if cron != "@specific":
                        start_date = croniter(cron, start_date).get_next(datetime)

                    reminder = Reminder(
                        creation_date=datetime.now(),
                        next_remind=start_date,
                        cron=cron,
                        message=message,
                        user=chat_id,
                    )
                    reminder.save(self.session)
                    self._send_message(chat_id, "Job was added")
                else:
                    self._send_message(
                        chat_id,
                        f"The first argument must be a cron valid command (including @daily, @hourly, etc...) or @specific",
                    )
            else:
                self._send_message(chat_id, f"Failed to parse command")
        else:
            logging.info("Unauthorized user tried to add a job")

    def _command_showjobs(self, update, context):
        """This function will respond to the ``/showjobs`` command.

        This will check if the user is allowed to use the bot. If he is,
        this will display all the reminders associated with the user,
        in an array.

        This function seems complicated but is only making computations
        to render the array nicely.

        Args:
            update (telegram.Update): update associated with the command.
            context (object): context associated with the command.
        """
        chat_id = update.effective_chat.id
        if (
            chat_id in self.config.allowed_users
            or self.config.user_policy == self.config.ALLOWED_USER_ALL
        ):
            reminds = Reminder.get_reminders_user(chat_id, self.session)
            if reminds:
                # Get maximums for array shaping
                id_max_len = max(
                    len("Id"), max([len(str(remind.id)) for remind in reminds])
                )
                cron_max_len = max(
                    len("Cron"), max([len(str(remind.cron)) for remind in reminds])
                )
                paused_max_len = 6
                next_remind_max_len = max(
                    len("Next remind"),
                    max(
                        [
                            len(str(remind.next_remind.strftime(DATETIME_FORMAT)))
                            for remind in reminds
                        ]
                    ),
                )
                message_max_len = max(
                    len("Message"), max([len(remind.message) for remind in reminds])
                )

                # Define separator
                separator = (
                    "+"
                    + (id_max_len + 2) * "-"
                    + "+"
                    + (cron_max_len + 2) * "-"
                    + "+"
                    + (paused_max_len + 2) * "-"
                    + "+"
                    + (next_remind_max_len + 2) * "-"
                    + "+"
                    + (message_max_len + 2) * "-"
                    + "+"
                    + "\n"
                )

                # Define headline
                headline = (
                    "| "
                    + (id_max_len - len("Id")) * " "
                    + "Id | "
                    + (cron_max_len - len("Cron")) * " "
                    + "Cron | "
                    + (paused_max_len - len("Paused")) * " "
                    + "Paused | "
                    + (next_remind_max_len - len("Next remind")) * " "
                    + "Next remind | "
                    + (message_max_len - len("Message")) * " "
                    + "Message |"
                    + "\n"
                )

                res = "```\nMy jobs : \n"
                res += separator
                res += headline
                res += separator
                for remind in reminds:
                    res += (
                        "| "
                        + (id_max_len - len(str(remind.id))) * " "
                        + f"{remind.id} | "
                        + (cron_max_len - len(str(remind.cron))) * " "
                        + f"{remind.cron} | "
                        + (paused_max_len - len(str(remind.paused))) * " "
                        + f"{remind.paused} | "
                        + (
                            next_remind_max_len
                            - len(str(remind.next_remind.strftime(DATETIME_FORMAT)))
                        )
                        * " "
                        + f"{remind.next_remind.strftime(DATETIME_FORMAT)} | "
                        + (message_max_len - len(remind.message)) * " "
                        + f"{remind.message} |"
                        + "\n"
                    )
                    res += separator
                res += "```"

                # Here we need to specify the parsing mode explictely for the ```
                self._send_message(chat_id, res, parse_mode=telegram.ParseMode.MARKDOWN)
            else:
                self._send_message(chat_id, "You don't have any job")
        else:
            logging.info("Unauthorized user tried to displays job")

    def _command_pausejob(self, update, context):
        """This function will respond to the ``/pausejob`` command.

        This will check if the user is allowed to use the bot. If he is,
        this will parse the command according to
        /pausejob jobid
        or
        /pausejob@botusername jobid

        The function will then fetch the associated reminder (if it exists),
        and check that the user associated to the reminder is actually the user
        making the request. If it is, then the job is paused.

        Args:
            update (telegram.Update): update associated with the command.
            context (object): context associated with the command.
        """
        chat_id = update.effective_chat.id
        if (
            chat_id in self.config.allowed_users
            or self.config.user_policy == self.config.ALLOWED_USER_ALL
        ):
            command = update["message"]["text"]

            # Identify reminder_id
            result = re.search(r"^\/pausejob\S* (\d*)$", command)
            if result:
                reminder_id = int(result.group(1))
                reminder = Reminder.get(reminder_id, self.session)
                if reminder:
                    if reminder.user == chat_id:
                        reminder.pause(self.session)
                        logging.info(f"User {chat_id} has paused job {reminder_id}")
                        self._send_message(chat_id, f"The job {reminder_id} was paused")
                    else:
                        logging.warning(
                            f"User {chat_id} is not authorized to modify job {reminder_id}"
                        )
                        self._send_message(chat_id, "You are not the owner of this job")
                else:
                    logging.warning(
                        f"User {chat_id} tried to change inexistant job {reminder_id}"
                    )
                    self._send_message(chat_id, "This job does not exist")
            else:
                self._send_message(chat_id, "Failed to parse the command")
        else:
            logging.info("Unauthorized user tried to pause a job")

    def _command_resumejob(self, update, context):
        """This function will respond to the ``/resumejob`` command.

        This will check if the user is allowed to use the bot. If he is,
        this will parse the command according to
        /resumejob jobid
        or
        /resumejob@botusername jobid

        The function will then fetch the associated reminder (if it exists),
        and check that the user associated to the reminder is actually the user
        making the request. If it is, then the job is resumed.

        Args:
            update (telegram.Update): update associated with the command.
            context (object): context associated with the command.
        """
        chat_id = update.effective_chat.id
        if (
            chat_id in self.config.allowed_users
            or self.config.user_policy == self.config.ALLOWED_USER_ALL
        ):
            command = update["message"]["text"]

            # Identify reminder_id
            result = re.search(r"^\/resumejob\S* (\d*)$", command)
            if result:
                reminder_id = int(result.group(1))
                reminder = Reminder.get(reminder_id, self.session)
                if reminder:
                    if reminder.user == chat_id:
                        reminder.resume(self.session)
                        logging.info(f"User {chat_id} has resumed job {reminder_id}")
                        self._send_message(
                            chat_id, f"The job {reminder_id} was resumed"
                        )
                    else:
                        logging.warning(
                            f"User {chat_id} is not authorized to modify job {reminder_id}"
                        )
                        self._send_message(chat_id, "You are not the owner of this job")
                else:
                    logging.warning(
                        f"User {chat_id} tried to change inexistant job {reminder_id}"
                    )
                    self._send_message(chat_id, "This job does not exist")
            else:
                self._send_message(chat_id, "Failed to parse the command")
        else:
            logging.info("Unauthorized user tried to resume a job")

    def _command_deletejob(self, update, context):
        """This function will respond to the ``/deletejob`` command.

        This will check if the user is allowed to use the bot. If he is,
        this will parse the command according to
        /deletejob jobid
        or
        /deletejob@botusername jobid

        The function will then fetch the associated reminder (if it exists),
        and check that the user associated to the reminder is actually the user
        making the request. If it is, then the job gets deleted.

        Args:
            update (telegram.Update): update associated with the command.
            context (object): context associated with the command.
        """
        chat_id = update.effective_chat.id
        if (
            chat_id in self.config.allowed_users
            or self.config.user_policy == self.config.ALLOWED_USER_ALL
        ):
            command = update["message"]["text"]

            # Identify reminder_id
            result = re.search(r"^\/deletejob\S* (\d*)$", command)
            if result:
                reminder_id = int(result.group(1))
                reminder = Reminder.get(reminder_id, self.session)
                if reminder:
                    if reminder.user == chat_id:
                        reminder.delete(self.session)
                        logging.info(f"User {chat_id} has deleted job {reminder_id}")
                        self._send_message(
                            chat_id, f"The job {reminder_id} was deleted"
                        )
                    else:
                        logging.warning(
                            f"User {chat_id} is not authorized to delete job {reminder_id}"
                        )
                        self._send_message(chat_id, "You are not the owner of this job")
                else:
                    logging.warning(
                        f"User {chat_id} tried to delete inexistant job {reminder_id}"
                    )
                    self._send_message(chat_id, "This job does not exist")
            else:
                self._send_message(chat_id, "Failed to parse the command")
        else:
            logging.info("Unauthorized user tried to delete a job")
