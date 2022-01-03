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

import datetime

from croniter import croniter
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Integer, String, Boolean

Base = declarative_base()


class Reminder(Base):
    """This is the main database model.

    It represents a reminder instance.

    A due reminder is a reminder with next_remind < datetime.now() and
    paused is False.
    Ater the message is sent, the reminder should be updated, using
    the update_remind function that will use the cron value to get
    the next remind datetime.

    Attributes:
        id (int): primary key of the reminder.
        creation_date (datetime): creation date of the reminder.
        next_remind (datetime): datetime of the next remind.
        cron (str): the value of the cron job. It can also be @specific.
        message (str): message to send for the reminder.
        user (int): id of the user who created the reminder.
        paused (bool): True if the reminder is paused.
    """

    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True)
    creation_date = Column(DateTime)
    next_remind = Column(DateTime)
    cron = Column(String)
    message = Column(String)
    user = Column(Integer)
    paused = Column(Boolean, default=False)

    def save(self, session):
        """Save the current reminder.

        Args:
            session (sqlalchemy.orm.Session): session of sqlalchemy.
        """
        session.add(self)
        session.commit()

    def delete(self, session):
        """Delete the current reminder.

        Args:
            session (sqlalchemy.orm.Session): session of sqlalchemy.
        """
        session.delete(self)
        session.commit()

    def update_remind(self, session):
        """Update the reminder.

        This is only done when the cron is not "@specific" (in this case we delete the job).
        If the cron is anything else, we use the croniter.get_next function to find the next_remind value.

        Args:
            session (sqlalchemy.orm.Session): session of sqlalchemy
        """

        if self.cron == "@specific":
            self.delete()
        else:
            itr = croniter(self.cron, self.next_remind)
            self.next_remind = itr.get_next(datetime.datetime)

        self.save(session)

    def pause(self, session):
        """Pause the current reminder.

        Args:
            session (sqlalchemy.orm.Session): session of sqlalchemy.
        """
        self.paused = True
        self.save(session)

    def resume(self, session):
        """Resume the current reminder.

        The resume operation is not as simple as the pause operation
        This is due to the fact that the next_remind was left behind.

        Args:
            session (sqlalchemy.orm.Session): session of sqlalchemy.
        """

        if self.cron != "@specific":
            itr = croniter(self.cron, self.next_remind)
            now = datetime.datetime.now()
            while self.next_remind < now:
                self.next_remind = itr.get_next(datetime.datetime)
        self.paused = False
        self.save(session)

    def get_reminders_user(user, session):
        """Get all the reminders associated to one user.
        This functions returns all reminders (due or not due),
        (paused or not paused).

        Args:
            user (int): the id of the user.
            session (sqlalchemy.orm.Session): session of sqlalchemy.

        Returns:
            list<Reminder>: list of the reminders.
        """
        query = session.query(Reminder).filter(Reminder.user == user)
        return query.all()

    def get_all_reminders(session):
        """Get all reminders, independently of the user, paused status
        or due status.

        Args:
            session (sqlalchemy.orm.Session): session of sqlalchemy

        Returns:
            list<Reminder>: list of the reminders.
        """
        query = session.query(Reminder)
        return query.all()

    def get_all_due_reminders(session):
        """Get all due reminders (i.e. not paused and next_remind < now),
        independently of the user.

        Args:
            session (sqlalchemy.orm.Session): session of sqlalchemy

        Returns:
            list<Reminder>: list of the reminders.
        """
        now = datetime.datetime.now()
        query = (
            session.query(Reminder)
            .filter(Reminder.paused == False)
            .filter(Reminder.next_remind < now)
        )
        return query.all()

    def get(reminder_id, session):
        """Get a specific reminder.

        Args:
            reminder_id (int): id of the reminder.
            session (sqlalchemy.orm.Session): session of sqlalchemy.

        Returns:
            Reminder: reminder or None if the reminder does not exists.
        """
        try:
            reminder = session.query(Reminder).get(reminder_id)
        except Exception as e:
            print(e)
            reminder = None
        return reminder

    def equalize(session):
        """Equalize all reminders.

        This is the same operation as when we resume a reminder.

        This will get all the reminder to be placed to the valid
        next_remind just after now (this is to let no reminder running behind).

        This is to be runned once at the initialization of the bot.

        This function ignores paused job as the same function is runned when using
        the resume function.

        Args:
            session (sqlachemy.orm.Session): session of sqlalchemy.
        """
        query = session.query(Reminder).filter(Reminder.paused == False)
        now = datetime.datetime.now()
        for reminder in query.all():
            if reminder.cron != "@specific":
                itr = croniter(reminder.cron, reminder.next_remind)
                while reminder.next_remind < now:
                    reminder.next_remind = itr.get_next(datetime.datetime)
                reminder.save(session)

    def __str__(self):
        """Str representation of the reminder.

        Returns:
            str: str representation of the reminder.
        """
        return f"{self.id} - {self.cron} - {self.paused} - {self.next_remind} - {self.message} - {self.user}"