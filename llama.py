from openai import OpenAI
import logging


logging.basicConfig(filename='log_llama.log', level=logging.INFO, encoding='UTF-8', format='%(asctime)s - %(levelname)s - %(message)s')


def request_to_lamma(dialog_history, start_prompt=None, is_initiation=True):
    # Подключение к локально запущенному OpenAI API
    client = OpenAI(
        # base_url='http://ollama:11434/v1',
        base_url='http://localhost:11434/v1',
        api_key='ollama'
    )

    # while True:
    # user_input = input("Введите ваше сообщение ('stop' для завершения):\n")

    # Добавляем сообщение пользователя в историю диалога
    if is_initiation:
        dialog_history = [
            {
                "role": "system",
                "content": "Отвечай исключительно на русском языке и строго следуй инструкциям."
            },
            {
            "role": "user",
            "content": ''
                       f'{start_prompt} Текст: {dialog_history}'
        }]

    # Отправляем запрос к модели с текущей историей диалога
    logging.info('Модель думает')
    response = client.chat.completions.create(
        model="deepseek-r1:8b",
        messages=dialog_history,
        temperature=0.3,
        top_p=0.5,
        frequency_penalty=0.5
    )

    # Извлекаем содержимое ответа модели
    response_content = response.choices[0].message.content
    logging.info('Модель ответила')

    # Добавляем ответ модели в историю диалога
    dialog_history.append({
        "role": "assistant",
        "content": response_content,
    })

    return dialog_history
