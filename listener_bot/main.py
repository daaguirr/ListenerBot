import functools
import logging
import uuid
from typing import Iterator

from environs import Env
# noinspection PyPackageRequirements
from telegram import ReplyKeyboardRemove, Update, InlineKeyboardMarkup, InlineKeyboardButton
# noinspection PyPackageRequirements
from telegram.ext import Updater, ConversationHandler, CommandHandler, CallbackContext, \
    CallbackQueryHandler, MessageHandler, Filters

from models import Listener

env = Env()
env.read_env()

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

ENTER_DESCRIPTION, DISABLE_LISTENER = range(2)


def check_whitelist(func):
    whitelist = {}

    @functools.wraps(func)
    def inner(update: Update, context: CallbackContext):
        if update.message.chat_id not in whitelist:
            update.message.reply_text('Not allowed')
            return
        return func(update, context)

    return inner


# noinspection PyUnusedLocal
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi! I am Listener Bot and i can listen processes')
    logger.info(update.message)  # INIT: host the bot , send a /start , add chat_id (on this log) to whitelist


# noinspection PyUnusedLocal
def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


# noinspection PyUnusedLocal
def error(update: Update, context: CallbackContext, error_name):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error_name)


# noinspection PyUnusedLocal
def cancel(update: Update, context: CallbackContext):
    user = update.message.from_user
    logger.info("User %s canceled", user.first_name)
    update.message.reply_text('Canceled',
                              reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# noinspection PyUnusedLocal
def create_listener(update: Update, context: CallbackContext):
    update.message.reply_text(text=f"Please enter Description or /cancel",
                              reply_markup=ReplyKeyboardRemove())
    return ENTER_DESCRIPTION


# noinspection PyUnusedLocal
def create_listener_get_description(update: Update, context: CallbackContext):
    description = update.message.text
    chat_id: int = update.message.chat_id

    listener = Listener.create(chat_id=chat_id, description=description, key=str(uuid.uuid4()))
    update.message.reply_text(text=f"Create listener with key = {listener.key}",
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def get_current_listeners(chat_id):
    return Listener.select().where(Listener.chat_id == chat_id, not Listener.enable)


def get_listeners_inline(update: Update):
    listeners: Iterator[Listener] = get_current_listeners(update.message.chat_id)
    ls: Listener
    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text=f"{ls.description}",
                               callback_data=ls.id)] for ls in listeners])

    update.message.reply_text('Please select listener or /cancel',
                              reply_markup=markup)


# noinspection PyUnusedLocal
def disable_listener(update: Update, context: CallbackContext):
    get_listeners_inline(update)
    return DISABLE_LISTENER


# noinspection PyUnusedLocal
def disable_get_listener_name(update: Update, context: CallbackContext):
    listener_id = update.callback_query.data
    listener = Listener.get(Listener.id == listener_id)
    listener.enable = False
    listener.save()
    msg = f'Disable listener {listener.description}'
    update.effective_message.edit_text(msg)
    return ConversationHandler.END


def main():
    """Start the bot."""
    updater = Updater(env.str("BOT_KEY"), use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))

    # on noncommand i.e message - echo the message on Telegram
    create_listener_hand = ConversationHandler(
        entry_points=[CommandHandler('create_listener', create_listener)],

        states={
            ENTER_DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, create_listener_get_description)],
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dispatcher.add_handler(create_listener_hand)

    disable_listener_hand = ConversationHandler(
        entry_points=[CommandHandler('disable_listener', disable_listener)],

        states={
            DISABLE_LISTENER: [CallbackQueryHandler(disable_get_listener_name)],
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dispatcher.add_handler(disable_listener_hand)

    dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
