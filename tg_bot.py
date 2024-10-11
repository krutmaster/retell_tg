import asyncio
from aiogram import Bot, Dispatcher, types
from db import connect_to_db, execute_query
from aiogram.filters import Command
from secret import API_TOKEN


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
        res = eval(res[0][1])[-1]
        res = res['content']
        return [res, id_dialog]
    return False


async def update_dialog_from_bot(id_dialog: int, last_msg_id: int):
    # Подключаемся к базе данных
    conn = connect_to_db()
    # Открываем курсор для выполнения операций с БД
    cursor = conn.cursor()
    query = "update dialog set last_msg_id = %s where id = %s"
    params = (last_msg_id, id_dialog,)
    execute_query(conn, cursor, query, params)


async def send_answered_text(chat_id: int):
    """
    Функция отправки сообщения и вызова обновления диалога.
    """
    # Получаем текст для отправки
    res_query = await get_answered_text()
    if res_query is not False:
        text_to_send = res_query[0]
        id_dialog = res_query[1]

        # Отправляем текст пользователю
        sent_message = await bot.send_message(chat_id=chat_id, text=text_to_send)

        # Обновляем диалог на основе ID отправленного сообщения
        await update_dialog_from_bot(id_dialog, sent_message.message_id)


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
    # Регистрация хэндлеров
    # dp.message.register(send_welcome, Command(commands=["start"]))
    asyncio.create_task(periodic_task(538231919))
    asyncio.create_task(clear_db())

    # Запуск бота
    await dp.start_polling(bot)  # Старт polling для получения обновлений


if __name__ == '__main__':
    asyncio.run(main())
