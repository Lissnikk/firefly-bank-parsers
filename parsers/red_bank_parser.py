import pdfplumber
import pandas as pd
import re
import argparse

def parse_alfa_pdf(input_pdf, output_csv, account_name="Альфа-Счет"):
    transactions = []

    with pdfplumber.open(input_pdf) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"

    lines = text.split('\n')

    # Универсальный паттерн: дата + любой код операции (без пробелов) + описание + сумма
    # Сумма может быть с минусом или без
    date_pattern = re.compile(
        r'^(\d{2}\.\d{2}\.\d{4})\s+'           # Дата
        r'(\S+)\s+'                              # Код операции (любой набор символов без пробелов)
        r'(.+?)\s+'                              # Описание (ленивый захват)
        r'(-?\d[\d\s]*,\d{2}\s+RUR)$'            # Сумма (с опциональным минусом)
    )

    current_tx = None
    current_description = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = date_pattern.match(line)
        if match:
            # Сохраняем предыдущую транзакцию
            if current_tx:
                current_tx['description'] = ' '.join(current_description).strip()
                transactions.append(current_tx)

            date_str, code, desc_start, amount_str = match.groups()

            # Конвертируем дату
            d, m, y = date_str.split('.')
            date_fmt = f"{y}-{m}-{d}"

            # Парсим сумму СО ЗНАКОМ: "-6 010,00 RUR" -> -6010.00, "10 000,00 RUR" -> 10000.00
            amount_clean = re.sub(r'[^\d,\-]', '', amount_str).replace(',', '.')
            try:
                amount = float(amount_clean)
            except:
                amount = 0.0

            current_tx = {
                'date': date_fmt,
                'code': code,
                'amount': amount,  # Сохраняем со знаком!
                'source_name': account_name
            }
            current_description = [desc_start]
        elif current_tx:
            # Продолжение описания
            current_description.append(line)

    # Последняя транзакция
    if current_tx:
        current_tx['description'] = ' '.join(current_description).strip()
        transactions.append(current_tx)

    if transactions:
        df = pd.DataFrame(transactions)
        df = df[['date', 'amount', 'description', 'source_name']]
        df.to_csv(output_csv, index=False)
        print(f"✅ Сохранено {len(df)} транзакций в {output_csv}")
        print(f"\nПример (первые 5):")
        print(df.head().to_string())

        # Статистика
        income = df[df['amount'] > 0].shape[0]
        expense = df[df['amount'] < 0].shape[0]
        print(f"\n📊 Статистика:")
        print(f"  Доходы: {income}")
        print(f"  Расходы: {expense}")
    else:
        print("❌ Не удалось извлечь данные.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Конвертер выписки Альфа-Банка в CSV")
    parser.add_argument("input", help="Путь к PDF файлу")
    parser.add_argument("-o", "--output", default="firefly_import.csv", help="Выходной CSV файл")
    parser.add_argument("-a", "--account", default="Альфа-Счет", help="Название счета")

    args = parser.parse_args()
    parse_alfa_pdf(args.input, args.output, args.account)
