import asyncio
from datetime import timedelta
from time import time, sleep
from contextlib import suppress

from telethon import TelegramClient, events, sync, errors, custom
from db import connect_to_db, execute_query
import exceptions
from secret import api_id, api_hash


client = TelegramClient('opentfd_session', api_id, api_hash, system_version="4.16.30-vxCUSTOM").start()
last_msg = None
last_msg_time = None
MERGE_TIMEOUT = 30
merge_semaphore = asyncio.Semaphore(value=1)
draft_semaphore = asyncio.Semaphore(value=1)


@client.on(events.NewMessage(pattern=r'^!type->.*', outgoing=True))
async def typing_imitate(message: events.NewMessage.Event):
    text, text_out = str(message.raw_text).split('->')[-1], str()
    word = list(text)
    with suppress(Exception):
        for letter in word:
            text_out += letter
            try:
                if word.index(letter) % 2 == 1:
                    await message.edit(f'`{text_out}`|')
                else:
                    await message.edit(f'`{text_out}`')
                await asyncio.sleep(0.2)
            except errors.MessageNotModifiedError:
                continue


@client.on(events.NewMessage(incoming=True))
async def break_updater(event: events.NewMessage.Event):
    global last_msg, last_msg_time
    with suppress(Exception):
        if event.chat:
            if event.chat.bot:
                return
    with suppress(Exception):
        if last_msg:
            if event.chat_id == last_msg.chat_id:
                last_msg = None
                last_msg_time = None


@client.on(events.NewMessage(pattern=r'^/switchmerger', outgoing=True))
async def switch_merger(event: custom.Message):
    with suppress(Exception):
        chat_off = exceptions.chat_off
        if not event.chat_id in chat_off:
            chat_off.append(event.chat_id)
            status = 'was turned off'
        else:
            chat_off.remove(event.chat_id)
            status = 'was turned on'
        with open('exceptions.py', 'w') as file:
            file.write(f'chat_off = {str(chat_off)}')
        await event.edit(f'`Merger for this chat {status}`')


def format_message(message):
    sender = message.sender.first_name
    if message.sender.last_name:
        sender += f" {message.sender.last_name}"

    text = message.message
    return f"[СООБЩЕНИЕ] {sender}: {text}\n"


def add_text_to_db(text):
    # Подключаемся к базе данных
    conn = connect_to_db()
    # Открываем курсор для выполнения операций с БД
    cursor = conn.cursor()
    query = "insert into dialog (history) values (%s)"
    params = (text,)
    res = execute_query(conn, cursor, query, params)


# Обработка команды !retell только для исходящих сообщений (отправленных самим пользователем)
@client.on(events.NewMessage(outgoing=True, pattern='!retell'))
async def collect_msg_for_retell(event):
    # Проверка, что сообщение с командой является ответом на другое сообщение
    if not event.is_reply:
        await event.reply("Команда должна быть отправлена как ответ на сообщение.")
        return

    # Получаем все сообщения начиная с ответа
    # Получаем сообщение, на которое отправлен реплай
    reply_message = await event.get_reply_message()

    # Получаем все сообщения между реплаем и командой !retell
    # max_id: не включаем текущее сообщение с командой !retell
    messages = await client.get_messages(
        event.chat_id,
        min_id=reply_message.id - 1,  # Сообщения начиная с этого
        max_id=event.id - 1  # Сообщения до самого сообщения с командой (не включая его)
    )
    messages = list(reversed(messages))

    for_retell_text = []

    # Проходим по сообщениям, проверяя наличие текста
    for msg in messages:
        if msg.text or (msg.media and msg.message):
            for_retell_text.append(format_message(msg))

    # Если есть собранные сообщения, отправляем их пользователю
    if for_retell_text:
        add_text_to_db(for_retell_text)
        print('Text was added')
    else:
        print("Не найдено сообщений с текстом после ответа.")

    # Удаляем сообщение с командой !retell после выполнения всех действий
    await event.delete()


@client.on(events.NewMessage(outgoing=True))
async def merger(event: custom.Message):
    global last_msg
    global last_msg_time
    global merge_semaphore

    event_time = time()
    with suppress(Exception):
        if event.chat_id in exceptions.chat_off:
            return
        if event.text:
            if event.text.startswith('!bash') or event.text == '/switch_merger' or event.text == '!retell':
                return
        with suppress(Exception):
            if event.chat:
                if event.chat.bot:
                    return
        if (event.media or event.fwd_from or event.via_bot_id or
                event.reply_to_msg_id or event.reply_markup):
            last_msg = None
        elif last_msg is None or event.text.startswith('.'):
            if event.text.startswith('.'):
                last_msg = await event.edit(event.text[2:])
            else:
                last_msg = event
            last_msg_time = event_time
        elif last_msg.to_id == event.to_id:
            if event_time - last_msg_time < MERGE_TIMEOUT:
                try:
                    await merge_semaphore.acquire()
                    last_msg = await last_msg.edit('{0}\n{1}'.format(last_msg.text, event.text))
                    last_msg_time = event_time
                    await event.delete()
                finally:
                    merge_semaphore.release()
            else:
                last_msg = event
                last_msg_time = event_time
        else:
            last_msg = event
            last_msg_time = event_time


print('OpenTFD if running')
client.run_until_disconnected()
