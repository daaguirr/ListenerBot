import datetime
import functools
import json
import logging
import os
import subprocess
from typing import Callable

import telegram.ext
from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import Updater, Job, ConversationHandler, CommandHandler, MessageHandler, Filters
import random as rnd
from dataclasses import dataclass

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
JOBS = {}
TIME_END, PROCESS_PK, TIME_UPDATE, FILE_NAME, JOB_CANCEL = range(5)

time_dict = {
    "5seg": 5,
    "30seg": 30,
    "1min": 60,
    "2min": 120,
    "5min": 300,
    "10min": 600,
    "1hr": 3600,
    "12hr": 12 * 3600,
    "24hr": 24 * 3600
}

keyboard_time_keyboard = [["5seg"],
                          ["30seg"],
                          ["1min"],
                          ["2min"],
                          ["5min"],
                          ["10min"],
                          ["1hr"],
                          ["12hr"],
                          ["24hr"],
                          ]


@dataclass
class ListenEndContext:
    chat_id: int
    pk: str


@dataclass
class ListenFileContext:
    chat_id: int
    file_name: str
    last_update: str = None


with open('config.json', 'r') as f:
    config = json.load(f)


def check_whitelist(func):
    whitelist = {}

    @functools.wraps(func)
    def inner(update: telegram.Update, context: telegram.ext.CallbackContext):
        if update.message.chat_id not in whitelist:
            update.message.reply_text('Not allowed')
            return
        return func(update, context)

    return inner


# noinspection PyUnusedLocal
def start(update: telegram.Update, context: telegram.ext.CallbackContext):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi! I am Listener Bot and i can listen processes')
    logger.info(update.message)  # INIT: host the bot , send a /start , add chat_id (on this log) to whitelist


# noinspection PyUnusedLocal
def help(update: telegram.Update, context: telegram.ext.CallbackContext):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Possible commands : /listen_process_end, /listen_update_file, /shut_up')


# noinspection PyUnusedLocal,PyShadowingNames
def error(update: telegram.Update, context: telegram.ext.CallbackContext, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


# noinspection PyUnusedLocal
def cancel(update: telegram.Update, context: telegram.ext.CallbackContext):
    user = update.message.from_user
    logger.info("User %s canceled", user.first_name)
    update.message.reply_text('Canceled',
                              reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def register_job(job_fn: Callable[[str], Job], context: telegram.ext.CallbackContext) -> str:
    current_jobs = {**context.user_data['jobs']} if 'jobs' in context.user_data else {}
    key = rnd.randint(1000000, 9999999)
    while key in current_jobs:
        key = rnd.randint(1000000, 9999999)

    job = job_fn(str(key))
    current_jobs[str(key)] = job
    context.user_data['jobs'] = current_jobs
    return str(key)


def cancel_job(name: str, context: telegram.ext.CallbackContext) -> bool:
    current_jobs = {**context.user_data['jobs']} if 'jobs' in context.user_data else {}
    if name not in current_jobs:
        return False
    job: Job = current_jobs[name]
    job.schedule_removal()  # TODO: check if job is already terminated
    del current_jobs[name]  # WARNING: delete on job queue on next check
    return True


# noinspection PyUnusedLocal
def listen_process_end(update: telegram.Update, context: telegram.ext.CallbackContext):
    update.message.reply_text(text=f"Please enter time schedule",
                              reply_markup=ReplyKeyboardMarkup(keyboard_time_keyboard, one_time_keyboard=True))
    return TIME_END


def listen_process_end_select_time(update: telegram.Update, context: telegram.ext.CallbackContext):
    time_text = update.message.text
    time = time_dict[time_text]
    context.user_data['delta'] = time
    update.message.reply_text('Please enter pk of process or /cancel', reply_markup=ReplyKeyboardRemove())
    return PROCESS_PK


def listen_process_end_select_process(update: telegram.Update, context: telegram.ext.CallbackContext):
    pk = update.message.text
    delta = context.user_data['delta']

    del context.user_data['delta']
    job_fn = lambda name: context.job_queue.run_repeating(check_end,
                                                          interval=delta, first=0,
                                                          context=ListenEndContext(update.message.chat_id, pk),
                                                          name=name)
    name_job = register_job(job_fn, context)
    context.bot.send_message(chat_id=update.message.chat_id,
                             text=f'Started listener with name = {name_job}')

    return ConversationHandler.END


# noinspection PyUnusedLocal
def shut_up(update: telegram.Update, context: telegram.ext.CallbackContext):
    update.message.reply_text('Please enter name of listener to finish or /cancel', reply_markup=ReplyKeyboardRemove())
    return JOB_CANCEL


def shut_up_get_job_name(update: telegram.Update, context: telegram.ext.CallbackContext):
    name = str(update.message.text)
    val = cancel_job(name, context)
    msg = f'Finished listener with name = {name}' if val else f'Error in finish job with name {name} '
    context.bot.send_message(chat_id=update.message.chat_id,
                             text=msg)
    return ConversationHandler.END


def check_end(context: telegram.ext.CallbackContext):
    job: Job = context.job
    data: ListenEndContext = context.job.context
    context.bot.send_message(chat_id=data.chat_id, text=f'BEEP {data.pk}')

    p1 = subprocess.Popen(["ps", "-o", "pid=", "-p", data.pk], stdout=subprocess.PIPE)
    res = p1.communicate()
    if res[0] == b'':
        context.bot.send_message(chat_id=data.chat_id, text=f'Process with pk = {data.pk} finished')
        job.schedule_removal()


# noinspection PyUnusedLocal
def listen_update_file(update: telegram.Update, context: telegram.ext.CallbackContext):
    update.message.reply_text(text=f"Please enter time schedule",
                              reply_markup=ReplyKeyboardMarkup(keyboard_time_keyboard, one_time_keyboard=True))
    return TIME_UPDATE


def listen_process_update_select_time(update: telegram.Update, context: telegram.ext.CallbackContext):
    time_text = update.message.text
    time = time_dict[time_text]
    context.user_data['delta'] = time
    update.message.reply_text('Please enter the path of file to listen or /cancel', reply_markup=ReplyKeyboardRemove())
    return FILE_NAME


def listen_process_update_select_file(update: telegram.Update, context: telegram.ext.CallbackContext):
    file_name = update.message.text
    delta = context.user_data['delta']

    del context.user_data['delta']
    job_fn = lambda name: context.job_queue.run_repeating(check_update,
                                                          interval=delta, first=0,
                                                          context=ListenFileContext(update.message.chat_id, file_name),
                                                          name=name)
    if not os.path.exists(file_name):
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text=f'WANING file with name = {file_name} does not exists')
    name_job = register_job(job_fn, context)
    context.bot.send_message(chat_id=update.message.chat_id,
                             text=f'Started listener with name = {name_job}')

    return ConversationHandler.END


def check_update(context: telegram.ext.CallbackContext):
    job: Job = context.job
    data: ListenFileContext = job.context

    last_update = data.last_update
    update = os.path.getmtime(data.file_name) if os.path.exists(data.file_name) else None

    if update is None:
        return

    date = datetime.datetime.fromtimestamp(update)

    if last_update is None:
        context.bot.send_message(
            chat_id=data.chat_id,
            text=f'When listener started to listen and file exists, last modified date is {date}')
        context.job.context.last_update = update

    elif update != last_update:
        with open(data.file_name, 'r') as file:
            value = file.read()

        context.bot.send_message(chat_id=data.chat_id,
                                 text=f'Update at {date} on file {data.file_name} with value: \n\n {value}')
        context.job.context.last_update = update


def main():
    """Start the bot."""
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(config["BOT_KEY"], use_context=True)
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    shut_up_hand = ConversationHandler(
        entry_points=[CommandHandler('shut_up', shut_up)],

        states={
            JOB_CANCEL: [MessageHandler(Filters.text, shut_up_get_job_name)],

        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(shut_up_hand)

    listen_end = ConversationHandler(
        entry_points=[CommandHandler('listen_process_end', listen_process_end)],

        states={
            TIME_END: [MessageHandler(Filters.regex('^(5seg|30seg|1min|2min|5min|10min|1hr|12hr|24hr)$'),
                                      listen_process_end_select_time)],
            PROCESS_PK: [MessageHandler(Filters.text, listen_process_end_select_process)]

        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(listen_end)

    listen_update = ConversationHandler(
        entry_points=[CommandHandler('listen_update_file', listen_update_file)],

        states={
            TIME_UPDATE: [MessageHandler(Filters.regex('^(5seg|30seg|1min|2min|5min|10min|1hr|12hr|24hr)$'),
                                         listen_process_update_select_time)],
            FILE_NAME: [MessageHandler(Filters.command, listen_process_update_select_file)]

        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(listen_update)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
