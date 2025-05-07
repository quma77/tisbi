import sqlite3
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = '7768917073:AAHumxZPNj6VOa6a4qypanUkvBNRuxaOL14'

# --- Функции для работы с базой данных ---
def create_connection():
    return sqlite3.connect('users.db')

def create_table():
    with create_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                address TEXT,
                phone TEXT,
                need_call BOOLEAN DEFAULT FALSE
            )
        ''')

def get_user(user_id):
    with create_connection() as conn:
        cursor = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        return cursor.fetchone()

def update_user(user_id, **kwargs):
    with create_connection() as conn:
        fields = ', '.join([f'{key} = ?' for key in kwargs])
        values = list(kwargs.values()) + [user_id]
        conn.execute(f'UPDATE users SET {fields} WHERE id = ?', values)
        conn.commit()

def insert_user(user_id, name, address, phone):
    with create_connection() as conn:
        conn.execute('INSERT INTO users (id, name, address, phone) VALUES (?, ?, ?, ?)', (user_id, name, address, phone))
        conn.commit()


# --- Обработчики команд и сообщений ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if user:
        name, address, phone, need_call = user[1:]
        message = f"Ваши данные:\nИмя: {name}\nАдрес: {address}\nТелефон: {phone}"
        keyboard = create_edit_keyboard(need_call)
        await update.message.reply_text(message, reply_markup=keyboard)
    else:
        await update.message.reply_text('Привет! Пожалуйста, введи свое имя:')
        context.user_data['step'] = 'name'


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    step = context.user_data.get('step')

    if step == 'name':
        context.user_data['name'] = text
        await update.message.reply_text('Введите ваш адрес:')
        context.user_data['step'] = 'address'
    elif step == 'address':
        context.user_data['address'] = text
        await update.message.reply_text('Введите ваш номер телефона:')
        context.user_data['step'] = 'phone'
    elif step == 'phone':
        context.user_data['phone'] = text
        insert_user(user_id, context.user_data['name'], context.user_data['address'], context.user_data['phone'])
        keyboard = create_edit_keyboard(False)
        await update.message.reply_text('Ваши данные сохранены!', reply_markup=keyboard)
        context.user_data.clear()
    elif update.message.text in ['Изменить имя', 'Изменить адрес', 'Изменить телефон']:
        context.user_data[f'waiting_for_{update.message.text.lower().replace(" ", "_")}'] = True
        await update.message.reply_text(f'Введите новое {update.message.text.lower()}:')
    elif context.user_data.get('waiting_for_name'): #Обработка изменения имени
        update_user(user_id, name=text)
        await update.message.reply_text(f"Имя успешно изменено на: {text}")
        context.user_data['waiting_for_name'] = False
        await start(update, context)
    elif context.user_data.get('waiting_for_address'): #Обработка изменения адреса
        update_user(user_id, address=text)
        await update.message.reply_text(f"Адрес успешно изменен на: {text}")
        context.user_data['waiting_for_address'] = False
        await start(update, context)
    elif context.user_data.get('waiting_for_phone'): #Обработка изменения телефона
        update_user(user_id, phone=text)
        await update.message.reply_text(f"Телефон успешно изменен на: {text}")
        context.user_data['waiting_for_phone'] = False
        await start(update, context)


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'edit_name':
        await query.edit_message_text("Введите новое имя:", reply_markup=None) # Убрали ReplyKeyboardRemove()
        context.user_data['waiting_for_name'] = True
    elif query.data == 'edit_address':
        await query.edit_message_text("Введите новый адрес:", reply_markup=None) # Убрали ReplyKeyboardRemove()
        context.user_data['waiting_for_address'] = True
    elif query.data == 'edit_phone':
        await query.edit_message_text("Введите новый номер телефона:", reply_markup=None) # Убрали ReplyKeyboardRemove()
        context.user_data['waiting_for_phone'] = True
    elif query.data == 'order_call':
        update_user(user_id, need_call=True)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Отменить звонок", callback_data='cancel_call')]])
        await query.edit_message_reply_markup(keyboard)
    elif query.data == 'cancel_call':
        update_user(user_id, need_call=False)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Заказать звонок", callback_data='order_call')]])
        await query.edit_message_reply_markup(keyboard)

def create_edit_keyboard(need_call):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Изменить имя", callback_data='edit_name')],
        [InlineKeyboardButton("Изменить адрес", callback_data='edit_address')],
        [InlineKeyboardButton("Изменить телефон", callback_data='edit_phone')],
        [InlineKeyboardButton("Заказать звонок", callback_data='order_call')] if not need_call else [InlineKeyboardButton("Отменить звонок", callback_data='cancel_call')]
    ])
    return keyboard

# --- Запуск бота ---
def main():
    create_table()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_button))

    application.run_polling()

if __name__ == '__main__':
    main()