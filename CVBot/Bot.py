import pandas as pd
import matplotlib.pyplot as plt
from telegram import InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler

#не забыть про этот блок кода
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

SELECT_ACTION, GET_PIVOT_ARGS = range(2)

async def start(update, context) -> None:
    keyboard = [
        [InlineKeyboardButton("Файл", callback_data='file')],
        [InlineKeyboardButton("График", callback_data='image')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text('Выберите вид представления?', reply_markup=reply_markup)
    return SELECT_ACTION

async def select_action(update, context) -> None:
    query = update.callback_query
    context.user_data['action'] = query.data

    await query.answer()
    await query.edit_message_text(
        text="Введите 'values' и 'index' через запятую для составления отчета:")
    return GET_PIVOT_ARGS

async def get_pivot_args(update, context) -> None:
    try:
        args = update.message.text.split(',')
        values = args[0].strip()
        index = args[1].strip()
        context.user_data['values'] = values
        context.user_data['index'] = index
    except IndexError:
        await update.message.reply_text("Ошибка!.")
        return GET_PIVOT_ARGS

    await update.message.reply_text("Отправьте CSV-файл для создания отчета.")
    return ConversationHandler.END

async def handle_file(update, context) -> None:
    file = await update.message.document.get_file()
    await file.download_to_drive('input.csv')

    df = pd.read_csv('input.csv')

    values = context.user_data.get('values', 'Value')
    index = context.user_data.get('index', 'Category')

    pivot_table = pd.pivot_table(df, values=values, index=[index], aggfunc='sum')

    if context.user_data['action'] == 'file':
        pivot_table.to_csv('output.csv')
        with open('output.csv', 'rb') as f:
            await update.message.reply_document(document=InputFile(f), filename='pivot_table.csv')
    else:
        plt.figure(figsize=(6, 4))
        pivot_table.plot(kind='bar', color='skyblue')
        plt.title(f'Report: {index} vs {values}')
        plt.xlabel(index)
        plt.ylabel(values)

        image_path = 'report.png'
        plt.savefig(image_path)
        plt.close()

        with open(image_path, 'rb') as f:
            await update.message.reply_photo(photo=InputFile(f), filename='report.png')

def main():
    application = Application.builder().token(config.TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_ACTION: [CallbackQueryHandler(select_action)],
            GET_PIVOT_ARGS: [MessageHandler(filters.TEXT, get_pivot_args)],
        },
        fallbacks=[]
    )

    application.add_handler(conv_handler)

    application.add_handler(MessageHandler(filters.Document.FileExtension("csv"), handle_file))

    application.run_polling()


if __name__ == '__main__':
    main()
