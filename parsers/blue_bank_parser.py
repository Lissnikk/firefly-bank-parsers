import pdfplumber
import pandas as pd
import re
import argparse

def parse_vtb_pdf(input_pdf, output_csv, account_name="ВТБ-Карта"):
    transactions = []

    with pdfplumber.open(input_pdf) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"

    lines = text.split('\n')

    # Собираем операции из разрозненных строк
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Ищем строку с датой операции (DD.MM.YYYY)
        date_match = re.match(r'^(\d{2}\.\d{2}\.\d{4})$', line)
        if date_match and i + 2 < len(lines):
            op_date = date_match.group(1)

            # Следующая строка: дата обработки + суммы + описание
            proc_line = lines[i + 1].strip()
            # Строка после неё: время
            time_line = lines[i + 2].strip()

            # Паттерн для строки обработки:
            # DD.MM.YYYY -83.0 RUB -83.0 0.0 RUB Описание
            proc_pattern = re.compile(
                r'^(\d{2}\.\d{2}\.\d{4})\s+'              # Дата обработки
                r'(-?\d+\.?\d*)\s+RUB\s+'                 # Сумма в валюте операции
                r'(-?\d+\.?\d*)\s+'                       # Сумма в валюте карты
                r'(-?\d+\.?\d*)\s+RUB\s+'                 # Комиссия
                r'(.+)$'                                  # Описание
            )

            proc_match = proc_pattern.match(proc_line)
            if proc_match:
                proc_date, amount_op, amount_card, commission, desc = proc_match.groups()

                # Конвертируем дату операции в YYYY-MM-DD
                d, m, y = op_date.split('.')
                date_fmt = f"{y}-{m}-{d}"

                # Используем сумму в валюте карты (уже с правильным знаком)
                try:
                    amount = float(amount_card)
                except:
                    amount = 0.0

                desc = ' '.join(desc.split())

                transactions.append({
                    'date': date_fmt,
                    'amount': amount,
                    'description': desc,
                    'source_name': account_name
                })
                i += 3  # Пропускаем 3 строки
                continue

        i += 1

    if transactions:
        df = pd.DataFrame(transactions)
        df = df[['date', 'amount', 'description', 'source_name']]
        df.to_csv(output_csv, index=False)
        print(f"✅ ВТБ: сохранено {len(df)} транзакций в {output_csv}")

        income = df[df['amount'] > 0].shape[0]
        expense = df[df['amount'] < 0].shape[0]
        print(f"  Доходы: {income}, Расходы: {expense}")
    else:
        print("❌ Не удалось извлечь данные из ВТБ")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Конвертер выписки ВТБ в CSV")
    parser.add_argument("input", help="Путь к PDF файлу")
    parser.add_argument("-o", "--output", default="vtb_import.csv", help="Выходной CSV файл")
    parser.add_argument("-a", "--account", default="ВТБ-Карта", help="Название счета")

    args = parser.parse_args()
    parse_vtb_pdf(args.input, args.output, args.account)
