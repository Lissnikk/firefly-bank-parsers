import pdfplumber
import pandas as pd
import re
import argparse

def parse_sber_pdf(input_pdf, output_csv, account_name="Сбер-Карта"):
    transactions = []

    with pdfplumber.open(input_pdf) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"

    lines = text.split('\n')

    # Паттерн для первой строки операции:
    # DD.MM.YYYY HH:MM КАТЕГОРИЯ СУММА ОСТАТОК
    line1_pattern = re.compile(
        r'^(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})\s+'  # Дата и время
        r'(.+?)\s+'                                    # Категория
        r'([\+\-]?\s*\d[\d\s]*,\d{2})\s+'              # Сумма
        r'(\d[\d\s]*,\d{2})$'                          # Остаток
    )

    # Паттерн для второй строки операции:
    # DD.MM.YYYY КОД ОПИСАНИЕ
    line2_pattern = re.compile(
        r'^(\d{2}\.\d{2}\.\d{4})\s+(\d+)\s+(.+)$'      # Дата обработки, код, описание
    )

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        match1 = line1_pattern.match(line)
        if match1:
            date_str, time_str, category, amount_str, balance = match1.groups()

            # Ищем следующую строку с описанием
            if i + 1 < len(lines):
                line2 = lines[i + 1].strip()
                match2 = line2_pattern.match(line2)

                if match2:
                    proc_date, auth_code, desc = match2.groups()

                    # Конвертируем дату в YYYY-MM-DD
                    d, m, y = date_str.split('.')
                    date_fmt = f"{y}-{m}-{d}"

                    # Парсим сумму: "+1 000,00" -> 1000.00, "600,00" -> -600.00
                    amount_clean = re.sub(r'[^\d,\+\-]', '', amount_str).replace(',', '.')
                    try:
                        amount = float(amount_clean)
                        if '+' not in amount_str and amount > 0:
                            amount = -amount
                    except:
                        amount = 0.0

                    desc = ' '.join(desc.split())

                    transactions.append({
                        'date': date_fmt,
                        'amount': amount,
                        'description': f"{category} - {desc}",
                        'source_name': account_name
                    })
                    i += 2  # Пропускаем следующую строку
                    continue

        i += 1

    if transactions:
        df = pd.DataFrame(transactions)
        df = df[['date', 'amount', 'description', 'source_name']]
        df.to_csv(output_csv, index=False)
        print(f"✅ Сбербанк: сохранено {len(df)} транзакций в {output_csv}")

        income = df[df['amount'] > 0].shape[0]
        expense = df[df['amount'] < 0].shape[0]
        print(f"  Доходы: {income}, Расходы: {expense}")
    else:
        print("❌ Не удалось извлечь данные из Сбербанка")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Конвертер выписки Сбербанка в CSV")
    parser.add_argument("input", help="Путь к PDF файлу")
    parser.add_argument("-o", "--output", default="sber_import.csv", help="Выходной CSV файл")
    parser.add_argument("-a", "--account", default="Сбер-Карта", help="Название счета")

    args = parser.parse_args()
    parse_sber_pdf(args.input, args.output, args.account)
