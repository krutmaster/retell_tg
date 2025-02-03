from openai import OpenAI


def request_to_lamma(dialog_history, start_prompt=None, is_initiation=True):
    # Подключение к локально запущенному OpenAI API
    client = OpenAI(
        base_url='http://ollama:11434/v1',
        # base_url='http://localhost:11434/v1',
        api_key='ollama'
    )

    # while True:
    # user_input = input("Введите ваше сообщение ('stop' для завершения):\n")

    # Добавляем сообщение пользователя в историю диалога
    if is_initiation:
        dialog_history = [{
            "role": "user",
            "content": ''
                       f'Текст: {dialog_history}'
        }]

    print('\nЛама думает, ожидайте...')
    # Отправляем запрос к модели с текущей историей диалога
    response = client.chat.completions.create(
        model="deepseek-r1:8b",
        messages=dialog_history,
        # temperature=0.3,
        top_p=0.8,
        frequency_penalty=0.3
    )

    # Извлекаем содержимое ответа модели
    response_content = response.choices[0].message.content
    print("\nОтвет модели:", response_content)

    # Добавляем ответ модели в историю диалога
    dialog_history.append({
        "role": "assistant",
        "content": response_content,
    })

    return dialog_history
