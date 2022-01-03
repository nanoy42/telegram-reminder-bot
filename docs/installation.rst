Installation
============

Getting the software
--------------------

There are several ways of getting the ``telegram-reminder-bot`` software, the simpler being using pip.

With pip
^^^^^^^^

You can install the package using the command

.. code-block:: bash

    pip install telegram-reminder-bot

With a git clone
^^^^^^^^^^^^^^^^

You clone the repository from github. This will allow easier updates when new code is released :

.. code-block:: bash

    git clone https://github.com/nanoy42/telegram-reminder-bot

You can then install the dependencies using poetry or pip :

Using poetry 
""""""""""""

.. code-block:: bash

    poetry install

or if you only want the dependencies and not the ``telegram-reminder-bot`` package to be installed :

.. code-block:: bash

    poetry install --no-root

.. note::

    If you want to use the daemonized version, you will need extra dependencies : ``poetry install -E daemons`` or ``poetry install -E daemons --no-root``

You can install dev dependencies using 

.. code-block:: bash

    poetry install --dev

Using pip
"""""""""

You can install the dependencies using the following command :

.. code-block:: bash

    pip install -r requirements.txt

You can also install the dev dependencies using :

.. code-block:: bash

    pip install -r dev-requirements.txt

From source
^^^^^^^^^^^

You can download the latest release here : https://github.com/nanoy42/telegram-reminder-bot/releases

You can then install the dependencies using poetry or pip :

Using poetry 
""""""""""""

.. code-block:: bash

    poetry install

or if you only want the dependencies and not the ``telegram-reminder-bot`` package to be installed :

.. code-block:: bash

    poetry install --no-root

.. note::

    If you want to use the daemonized version, you will need extra dependencies : ``poetry install -E daemons`` or ``poetry install -E daemons --no-root``

You can install dev dependencies using 

.. code-block:: bash

    poetry install --dev

Using pip
"""""""""

You can install the dependencies using the following command :

.. code-block:: bash

    pip install -r requirements.txt

You can also install the dev dependencies using :

.. code-block:: bash

    pip install -r dev-requirements.txt

Database
--------

You will need a working database to use the bot. Any database that is compatible with `sqlalchemy <https://www.sqlalchemy.org/>`__ (see https://docs.sqlalchemy.org/en/14/dialects/index.html for the list of supported databases).

The bot was explicitly tested with sqlite, it would probably work with other databases but it was not tested.

Configuration
-------------

The configuration file is the file holding the configuration for the telegram bot and the database.

You can create the default configuration file by calling: 

.. code-block:: bash

    telegram-reminder-bot init_config -c configuration_path

The default configuration file will be created at the configuration path.

The default configuration file looks like 

.. code-block:: ini

    ; telegram-reminder-bot Copyright (c) 2021-2022 Yoann Piétri
    ; 
    ; This software is released under the MIT License.
    ; https://opensource.org/licenses/MIT
    ;
    ; This is the configuration file for telegram-reminder-bot
    ; The configuration file is separated in two sections : telegram and db
    ; The first holds the token and the list of allowed users
    ; The second holds the engine configuration

    [telegram]
    ; Token of the telegram Bot in the format 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
    ; Default is 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
    token = 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

    ; List of allowed users, separated by commas. If 0 is included
    ; all users are considered to be allowed.
    ; An empty string means no user is allowed
    ; Default is an empty string
    allowed_users = 

    [db]
    ; Configuration of the engine. See https://docs.sqlalchemy.org/en/14/core/engines.html
    ; WARNING : relative path are not supported yet for daemonized mode.
    ; Default is sqlite:////var/telegram-reminder-bot/db.db
    engine = sqlite:////var/telegram-reminder-bot/db.db

    [logs]
    ; Path for the logs
    ; If no path is given, no logs are written
    ; Default is /var/log/telegram-reminder-bot.log
    path = /var/log/telegram-reminder-bot.log

telegram
^^^^^^^^

.. attribute:: token

    The token of the telegram bot, in the format 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11 (without ``bot`` at the beginning). Default is ``123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11``.

.. attribute:: allowed_users

    The list of allowed users and chats to use the bot. This as to be the list of IDs of users and chats separated by commas. If the list is empty, no user or chat is allowed to user the bot. If the list contains a ``0``, then all users and chats are allowed to use the bot. Default is an empty string.

.. note::

    This is maybe the moment to speak of the behavior of this bot inside a group.
    Please keep in mind that this was **not** tested and this is only a prediction of what will happen.

    The reminder will be associated to the chat id, and not a user id, if of course the chat id is in the list of allowed users in the configuration.
    Hence, everyone in the chat will be able to make modifications on the jobs.
    
    I would not recommend the usage of this bot, as it is, in a chat. Hence, in the documentation I will refer as a user using the bot.

db
^^

.. attribute:: engine

    The database configuration. See https://docs.sqlalchemy.org/en/14/dialects/index.html for documentation. Default is ``sqlite:////var/telegram-reminder-bot/db.db``.

.. warning:: 

    Relative paths are not supported yet when using the daemonized mode. Please use absolute paths.

logs
^^^^

.. attribute:: path

    Path for the log file. If none is given, no logs are written. Default to /var/log/telegram-reminder-bot.log

Init database
-------------

Before using the bot, the database must be initialized.

There is a command line instruction in the ``telegram-reminder-bot`` script to initialize the database (``init_db``) :

.. code-block:: bash

    telegram-reminder-bot init_db -c config.ini


.. warning::

    This code is released as alpha version and therefore the structure of the databse is likely to evolve in the future and no migration infrastructure was planned in this version. While we will try to provide ways of migrating, we cannot ensure for now that the migration of the data will be simple.

Starting and stop the bot
-------------------------

The bot may be started using the ``entrypoint.py`` script. If the package was installed using pip the command ``telegram-reminder-bot`` is equivalent.

This command may be used as 

.. code-block:: bash

    usage: telegram-reminder-bot [-h] [-c CONFIGURATION_FILE] {start,stop,restart,debug,init_db}

    Telegram reminder bot v0.1.0

    positional arguments:
    {start,stop,restart,debug,init_db,init_config}

    options:
    -h, --help            show this help message and exit
    -c CONFIGURATION_FILE, --configuration-file CONFIGURATION_FILE
                            Path of the configuration file. Default to /etc/telegram-reminder-bot/config.ini

The possible actions are 

* start : start the bot, in daemon mode (requires the ``daemons`` package).
* stop : stop the bot, in daemon mode (requires the ``daemons`` package).
* restart : restart the bot, in daemon mode (requires the ``daemons`` package).
* debug : start the bot directly with debug level for logs
* init_db : initialize the database.
* init_config : copy the default configuration file to the location given by ``-c`` or ``--configuration-file`` (``/etc/telegram-reminder-bot/config.ini`` by default).

The path of the configuration file can be given using the ``-c`` of ``--configuration-file`` option. The default value for the option is ``/etc/telegram-reminder-bot/config.ini``.

The documentation of the command can be accessed using ``--help``.

Full example
------------

This a full example of a quickstart to run the bot :

.. code-block:: bash

    $ pip install telegram-reminder-bot
    [...]
    $ telegram-reminder-bot -h
    usage: telegram-reminder-bot [-h] [-c CONFIGURATION_FILE] {start,stop,restart,debug,init_db,init_config}

    Telegram reminder bot v0.1.0

    positional arguments:
    {start,stop,restart,debug,init_db,init_config}

    options:
    -h, --help            show this help message and exit
    -c CONFIGURATION_FILE, --configuration-file CONFIGURATION_FILE
                            Path of the configuration file. Default to /etc/telegram-reminder-bot/config.ini
    
    $ telegram-reminder-bot init_config -c config.ini
    [OK] The default configuration file was copied to config.ini.

    $ ls
    config.ini

    $ cat config.ini
    ; telegram-reminder-bot Copyright (c) 2021-2022 Yoann Piétri
    ; 
    ; This software is released under the MIT License.
    ; https://opensource.org/licenses/MIT
    ;
    ; This is the configuration file for telegram-reminder-bot
    ; The configuration file is separated in two sections : telegram and db
    ; The first holds the token and the list of allowed users
    ; The second holds the engine configuration

    [telegram]
    ; Token of the telegram Bot in the format 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
    ; Default is 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
    token = 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

    ; List of allowed users, separated by commas. If 0 is included
    ; all users are considered to be allowed.
    ; An empty string means no user is allowed
    ; Default is an empty string
    allowed_users = 

    [db]
    ; Configuration of the engine. See https://docs.sqlalchemy.org/en/14/core/engines.html
    ; WARNING : relative path are not supported yet for daemonized mode.
    ; Default is sqlite:////var/telegram-reminder-bot/db.db
    engine = sqlite:////var/telegram-reminder-bot/db.db

    [logs]
    ; Path for the logs
    ; If no path is given, no logs are written
    ; Default is /var/log/telegram-reminder-bot.log
    path = /var/log/telegram-reminder-bot.log

    $ vim config.ini
    [...]

    $ cat config.ini
    ; telegram-reminder-bot Copyright (c) 2021-2022 Yoann Piétri
    ; 
    ; This software is released under the MIT License.
    ; https://opensource.org/licenses/MIT
    ;
    ; This is the configuration file for telegram-reminder-bot
    ; The configuration file is separated in two sections : telegram and db
    ; The first holds the token and the list of allowed users
    ; The second holds the engine configuration

    [telegram]
    ; Token of the telegram Bot in the format 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
    ; Default is 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
    token = **************

    ; List of allowed users, separated by commas. If 0 is included
    ; all users are considered to be allowed.
    ; An empty string means no user is allowed
    ; Default is an empty string
    allowed_users = ************

    [db]
    ; Configuration of the engine. See https://docs.sqlalchemy.org/en/14/core/engines.html
    ; WARNING : relative path are not supported yet for daemonized mode.
    ; Default is sqlite:////var/telegram-reminder-bot/db.db
    engine = sqlite:////home/nanoy/Projets/test-telegram-reminder-bot/db.db

    [logs]
    ; Path for the logs
    ; If no path is given, no logs are written
    ; Default is /var/log/telegram-reminder-bot.log
    path = telegram-reminder-bot.log

    $ telegram-reminder-bot init_db -c config.ini
    [OK] The database was successfully initialized

    $ ls
    config.ini  db.db

    $ telegram-reminder-bot start -c config.ini



