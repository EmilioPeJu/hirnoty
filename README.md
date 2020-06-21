# hirnoty

hirnoty is a simple telegram bot that allows executing scripts and getting
notifications.

## Getting started
### Installing
* Create virtualenv:
  ```bash
  $ virtualenv venv
  $ source venv/bin/activate
  ```

* Install: `pip install git+https://github.com/hir12111/hirnoty`

### Quickstart

* Get a token from the botfather and add it to `~/.config/hirnoty/config.py`
  following the format `TOKEN = '...'`

* Add the scripts you want to allow to the folder `~/.config/hirnoty/scripts`,
  make sure that the scripts are set as executable

* Start hirnoty: `hirnoty-ctl start`

You can now talk to the bot

## Bot commands
\exec {script_name}

Execute script with name {script_name}


\join {topic_name}

Subscribe to topic {topic_name}. Hirnoty offers a "log" topic where hirnoty
logs are sent.


\leave {topic_name}

Unsubscribe from topic {topic_name}.


\search {keywords}

Search and return files matching the list of keywords passed. If you want
to index new files, send a file to the bot and set the caption to the keywords
associated to that file.

## How to send data to a topic from other program

* Create a zmq socket of type PUSH
* Connect to the machine running hirnoty (tcp port 1234)
* Send a multipart message in which the first part is the topic name and
  the second part is the actual information you want to send

## Configuration parameters

The user configuration is `~/.config/hirnoty/config.py`

TOKEN (str): Bot token (required).

SCRIPT\_DIR (str): Path to scripts directory.

INDEX\_DIR (str): where new indexed files will be put.

ACL (list): list of ids of allowed users. Defaults to `None` (disabled)

LOGLEVEL (str): loglevel, choice between: `'error'`, `warning`, `'info'` or `'debug'`. Defaults to `'info'`.

BIND\_ADDRESS (str): address to receive the external messages from, defauls to '*:1234'

CONNECT\_ADDRESS (str): address to send messages to, defaults to '127.0.0.1:1234'.
This is used for pushing to internal topics, e.g. log topic.

OTP (str): path to a file with one time passwords (one per line) that will be
consume from end to beginning of the file, the password must be provided at
the end of the command. Defaults to None (disabled).

INVERTED_INDEX (bool): enable file indexing using an inverted index. Defaults to False.

## Built With
* [aiogram](https://github.com/aiogram/aiogram) Asynchronous library for
  Telegram Bot API
* [pyzmq](https://github.com/zeromq/pyzmq) The python binding for zeromq
