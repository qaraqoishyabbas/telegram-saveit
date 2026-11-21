import asyncio
import getpass

import qrcode
from telethon.errors import SessionPasswordNeededError


def print_qr_ascii(url):
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)


async def authorize_with_qr(
    client,
    qr_renderer=print_qr_ascii,
    password_callback=getpass.getpass,
    output=print,
):
    while not await client.is_user_authorized():
        try:
            qr_login = await client.qr_login()
        except SessionPasswordNeededError:
            password = password_callback("Введите пароль двухэтапной аутентификации: ")
            await client.sign_in(password=password)
            continue

        output("Отсканируйте QR-код: Telegram -> Настройки -> Устройства -> Подключить устройство")
        qr_renderer(qr_login.url)

        try:
            await qr_login.wait()
        except asyncio.TimeoutError:
            output("QR-код истёк. Создаю новый...")
        except SessionPasswordNeededError:
            password = password_callback("Введите пароль двухэтапной аутентификации: ")
            await client.sign_in(password=password)
