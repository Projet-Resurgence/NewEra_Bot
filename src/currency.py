"""
Currency utilities for NEBot.
Contains functions for converting numbers and amounts.
"""

def convert(nu: str) -> str:
    try:
        number = int(nu)
        return '{:,}'.format(number).replace(',', '.')
    except ValueError:
        try:
            number = float(nu)
            integer_part, decimal_part = str(number).split('.')
            formatted_integer_part = '{:,}'.format(int(integer_part)).replace(',', '.')
            return f"{formatted_integer_part},{decimal_part}"
        except ValueError:
            return "Invalid input"

def unconvert(nu: str):
    try:
        return int(nu.replace(".", "").replace(",", ""))
    except ValueError:
        return "Error: invalid conversion"

def amount_converter(amount, sender_balance):
    if isinstance(amount, int):
        payment_amount = amount
    elif isinstance(amount, str):
        if amount.lower() == "all":
            payment_amount = sender_balance
        elif amount.lower() == "mid":
            payment_amount = sender_balance // 2
        else:
            try:
                payment_amount = int(amount.replace(",", ""))
            except ValueError:
                try:
                    payment_amount = int(amount.replace(".", ""))
                except ValueError:
                    return
    else:
        return 
    return payment_amount
