import asyncio
from aiogram import Bot, Dispatcher, types
from db import connect_to_db, execute_query
from aiogram.filters import Command
from secret import API_TOKEN
from json import dumps as json_dumps
from json import loads as json_loads


# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


async def get_answered_text():
    # Подключаемся к базе данных
    conn = connect_to_db()
    # Открываем курсор для выполнения операций с БД
    cursor = conn.cursor()
    query = "select id, history from dialog where is_answered = %s and last_msg_id = %s limit 1;"
    params = ('true', '0',)
    res = execute_query(conn, cursor, query, params)
    if res:
        id_dialog = res[0][0]
        res = json_loads(res[0][1])
        res = res[-1]['content']
        return [res, id_dialog]
    return False


async def answer_update_dialog(id_dialog: int, last_msg_id: int):
    conn = connect_to_db()
    cursor = conn.cursor()
    query = "update dialog set last_msg_id = %s where id = %s"
    params = (last_msg_id, id_dialog,)
    execute_query(conn, cursor, query, params)


async def user_update_dialog(last_msg_id: int, user_text: str):
    conn = connect_to_db()
    cursor = conn.cursor()
    query = "select id, history from dialog where last_msg_id = %s"
    params = (last_msg_id,)
    res = execute_query(conn, cursor, query, params)
    if res:
        id_dialog = res[0][0]
        dialog_history = res[0][1]
        dialog_history = json_loads(dialog_history)
        dialog_history.append({
            "role": "user",
            "content": user_text,
        })
        dialog_history = json_dumps(dialog_history)
        conn = connect_to_db()
        cursor = conn.cursor()
        query = "update dialog set is_answered = %s, history = %s, last_msg_id = %s where id = %s"
        params = ('false', dialog_history, -1, id_dialog,)
        execute_query(conn, cursor, query, params)


async def split_text_to_chunks(text, max_length=4095):
    # Инициализируем пустой список для хранения отрывков текста
    chunks = []

    # Разделяем текст по длине max_length
    while len(text) > max_length:
        # Находим последнее место для разреза по пробелу в пределах max_length
        split_index = text[:max_length].rfind(" ")
        if split_index == -1:  # если пробела нет, режем точно по max_length
            split_index = max_length

        # Добавляем часть текста в список и обрезаем исходный текст
        chunks.append(text[:split_index])
        text = text[split_index:].lstrip()  # убираем лишние пробелы слева у оставшегося текста

    # Добавляем оставшийся текст как последний отрывок
    chunks.append(text)
    return chunks


async def send_answered_text(chat_id: int):
    """
    Функция отправки сообщения и вызова обновления диалога.
    """
    # Получаем текст для отправки
    res_query = await get_answered_text()
    if res_query is not False:
        id_dialog = res_query[1]
        text_to_send = res_query[0]

        if len(text_to_send) > 4095:
            text_to_send_chunks = await split_text_to_chunks(text_to_send)
            for text_to_send in text_to_send_chunks:
                await asyncio.sleep(3)
                sent_message = await bot.send_message(chat_id=chat_id, text=text_to_send)
        else:

            # Отправляем текст пользователю
            sent_message = await bot.send_message(chat_id=chat_id, text=text_to_send)

        # Обновляем диалог на основе ID отправленного сообщения
        await answer_update_dialog(id_dialog, sent_message.message_id)


@dp.message()
async def handle_user_message(message: types.Message):
    # Проверяем, является ли сообщение ответом на другое сообщение
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        # Если это ответ на сообщение бота, сохраняем ID сообщения и текст
        last_msg_id = message.reply_to_message.message_id
        user_text = message.text

        # Вызываем функцию user_update_dialog с сохраненными значениями
        await user_update_dialog(last_msg_id, user_text)
    else:
        # Если сообщение не является ответом на сообщение бота
        await message.reply("Пожалуйста, ответьте на сообщение бота, чтобы продолжить.")


async def periodic_task(chat_id: int):
    """
    Функция для запуска периодической отправки сообщений.
    """
    while True:
        await send_answered_text(chat_id)
        await asyncio.sleep(10)  # Интервал между отправкой сообщений (например, 10 секунд)


async def clear_db():
    """
    Функция для запуска периодической отправки сообщений.
    """
    while True:
        # Подключаемся к базе данных
        conn = connect_to_db()
        # Открываем курсор для выполнения операций с БД
        cursor = conn.cursor()
        query = "delete from dialog where date < NOW() - INTERVAL '3 days';"
        execute_query(conn, cursor, query)
        await asyncio.sleep(60*60*12)  # Интервал между отправкой сообщений (например, 10 секунд)


# async def send_welcome(message: types.Message):
#     """
#     Обработчик команды /start.
#     """
#     await message.answer("Привет! Я бот, который будет отправлять сообщения и обновлять диалоги.")


async def main():
    asyncio.create_task(periodic_task(538231919))
    asyncio.create_task(clear_db())

    # Запуск бота
    await dp.start_polling(bot)  # Старт polling для получения обновлений


if __name__ == '__main__':
    asyncio.run(main())
