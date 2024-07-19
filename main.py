import logging
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import executor
from aiocryptopay import AioCryptoPay, Networks
import aiosqlite
import config
import random 
import string





logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.TOKEN, parse_mode='HTML')
dp = Dispatcher(bot)

cryptopay = AioCryptoPay(config.CRYPTO_TOKEN, network=Networks.MAIN_NET)

async def add_bet(user_id):
    async with aiosqlite.connect('db.db') as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                bets = row[1] + 1
                await db.execute("UPDATE users SET bets = ? WHERE user_id = ?", (bets, user_id))
                await db.commit()
            else:
                await db.execute("INSERT INTO users (user_id, bets, viplat) VALUES (?, 1, 0)", (user_id,))
                await db.commit()

async def add_viplata(amount, user_id):
    async with aiosqlite.connect('db.db') as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                viplat = float(row[2]) + amount
                await db.execute("UPDATE users SET viplat = ? WHERE user_id = ?", (viplat, user_id))
                await db.commit()
            else:
                await db.execute("INSERT INTO users (user_id, bets, viplat) VALUES (?, 0, amount)", (user_id, amount))
                await db.commit()
                
async def pay_money(amount, id):
    try:
        payme = await cryptopay.create_check(asset='USDT', amount=amount)
        keyboard = types.InlineKeyboardMarkup()
        prize = types.InlineKeyboardButton(text="🎁", url=payme.bot_check_url)
        keyboard.add(prize)
     
        await bot.send_message(id, f'<b>[💸] Выплата:\n</b>\n<blockquote><b>Сумма: {amount}$</b></blockquote>', reply_markup=keyboard)
    except Exception as e:
        await bot.send_message(id, f'<b>[⛔] Ошибка...</b>\nНе удалось выплатить <b>{amount}</b>!\nНапишите администратору @KrasnovWork за выплатой')
        for admid in config.ADMIN_IDS:
            await bot.send_message(admid, f"<b>АЛЕ НАХУЙ!</b>\nБот не может создать выплату!\n\nЮзер: {id}\nСумма: {amount}\n\nЛог ошибки: <b>{e}</b>")
    		

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    stavka_button = types.InlineKeyboardButton(text="🎲 | Сделать ставку", url=config.pinned_link)
    kanal_button = types.InlineKeyboardButton(text="🎁 | Канал", url="https://t.me/DoxBet_casino")
    stats_button = types.InlineKeyboardButton(text="📊 | Статистика", callback_data='my_stats')
    keyboard.add(stavka_button)
    keyboard.add(kanal_button)
    keyboard.add(stats_button)
    await message.reply("[👋] <b>Добро пожаловать в игровую платформу, основаную на платежной системе CryptoBot</b>\n\n<blockquote>Скорее переходи в основной канал и делай ставку!</blockquote>", reply_markup=keyboard)
    
@dp.callback_query_handler(lambda query: query.data == 'my_stats')
async def statistics(query: types.InlineQuery):
    user_id = query.from_user.id
    async with aiosqlite.connect('db.db') as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                user_id = row[0]
                bets = row[1]
                viplat = row[2]
                message = f'''
<b>[📊] Статистика пользователя @{query.from_user.username}</b>

<blockquote>💲 | Ставок: <b>{bets}</b>
💸 | Выплат на сумму: <b>{viplat} $</b></blockquote>
'''
                await bot.send_message(user_id, message)
            else:
                await db.execute("INSERT INTO users (user_id, bets, viplat) VALUES (?, 0, 0)", (user_id,))
                message = f'''
<b>[📊] Статистика пользователя @{query.from_user.username}</b>

<blockquote>💲 | Ставок: <b>0</b>
💸 | Выплат на сумму: <b>0 $</b></blockquote>
'''
                await bot.send_message(user_id, message)

@dp.channel_post_handler(chat_id=config.PAY_ID)
async def handle_new_bet(message: types.Message):
    try:
        bet_usd = float(message.text.split("($")[1].split(").")[0])
        bet_coment = message.text.split("💬 ")[1]
        bet_comment = bet_coment.lower()
        player_name = message.text.split("отправил(а)")[0].strip()
        user = message.entities[0].user
        player_id = user.id
        keyboard = types.InlineKeyboardMarkup()
        url_button = types.InlineKeyboardButton(text="🎲 | Сделать ставку", url=config.pinned_link)
        await add_bet(player_id)
        keyboard.add(url_button)
        bet_design = config.bet.format(bet_usd=bet_usd, player_name=player_name, bet_comment=bet_comment)
        await bot.send_message(config.MAIN_ID, bet_design, reply_markup=keyboard)
        if bet_comment.startswith("куб"):
            if bet_comment in config.ag_dice:
                await handle_dice(message, bet_usd, bet_comment, player_id)
            elif bet_comment.startswith("футбол"):
                if bet_comment in config.ag_foot:
                    await handle_football(message, bet_usd, bet_comment, player_id)
            elif bet_comment.startswith("баскет"):
                if bet_comment in config.ag_basket:
                    await handle_foot(message, bet_usd, bet_comment, player_id)
            else:
                await bot.send_message(config.MAIN_ID, "<blockquote><b>💬 | Вы указали неверную игру!\n\n📌 |Напишите администратору @KrasnovWork за возвратом</b></blockquote>")
        else:
            await bot.send_message(config.MAIN_ID, "<blockquote><b>💬 | Вы указали неверную игру!\n\n📌 |Напишите администратору @KrasnovWork за возвратом</b></blockquote>")
    except IndexError:
        player_name = message.text.split("отправил(а)")[0].strip()
        await bot.send_message(config.MAIN_ID, f"<b>[⛔] Ошибка!</b>\n\n<blockquote><b>Игрок {player_name} не указал комментарий!\nНапиши в ТП из описания канала, и забери свои деньги!</b></blockquote>")
    except AttributeError as e:
        player_name = message.text.split("отправил(а)")[0].strip()
        await bot.send_message(config.MAIN_ID, f"<b>[⛔] Ошибка!</b>\n\n<blockquote><b>Не удалось распознать игрока {player_name}!\nНапиши в ТП из описания канала, и забери свои деньги! Проблема возникла из-за того, что у вас выключена пересылка!</b></blockquote>")
    except Exception as e:
        await bot.send_message(config.MAIN_ID, "<b>[⛔] Произошла неизвестная ошибка при обработке ставки!</b>")
        for admid in config.ADMIN_IDS:
            await bot.send_message(admid, f"АЛЬОУ\n\n{e}\nфикси сука")

async def handle_dice(message, bet_usd, bet_comment, player_id):
    dice_value = await bot.send_dice(chat_id=config.MAIN_ID)
    dice_value = dice_value.dice.value

    bet_type = bet_comment.split(" ")[1].lower()

    if bet_type == "меньше":
        if dice_value in [1, 2, 3]:
            win_amount = bet_usd * config.cef
            await handle_win(player_id, win_amount)
        else:
            await bot.send_message(config.MAIN_ID, "<blockquote><b>❌ | К сожалению, вы проиграли.</b></blockquote>")
    elif bet_type == "больше":
        if dice_value in [4, 5, 6]:
            win_amount = bet_usd * config.cef
            await handle_win(player_id, win_amount)
        else:
            await bot.send_message(config.MAIN_ID, "<blockquote><b>❌ | К сожалению, вы проиграли.</b></blockquote>")
    elif bet_type in ["чет", "четное", "чёт"]:
        if dice_value in [2, 4, 6]:
            win_amount = bet_usd * config.cef
            await handle_win(player_id, win_amount)
        else:
            await bot.send_message(config.MAIN_ID, "<blockquote><b>❌ | К сожалению, вы проиграли.</b></blockquote>")
    elif bet_type in ["нечет", "нечетное", "нечётное"]:
        if dice_value in [1, 3, 5]:
            win_amount = bet_usd * config.cef
            await handle_win(player_id, win_amount)
        else:
            await bot.send_message(config.MAIN_ID, "<blockquote><b>❌ | К сожалению, вы проиграли.</b></blockquote>")
    else:
        await bot.send_message(config.MAIN_ID, "<blockquote><b>💬 | Вы указали неверную игру!\n\n📌 |Напишите администратору @KrasnovWork за возвратом</b></blockquote>")

async def handle_foot(message, bet_usd, bet_comment, player_id):
    footemoji = await bot.send_dice(chat_id=config.MAIN_ID, emoji="⚽")
    foot_value = dice_value.dice.value

    bet_type = bet_comment.split(" ")[1].lower()

    if bet_type in ['гол', 'голл']:
        if foot_value in [4, 5, 6]:
            win_amount = bet_usd * config.cef
            await handle_win(player_id, win_amount)
        else:
            await bot.send_message(config.MAIN_ID, "<blockquote><b>❌ | К сожалению, вы проиграли.</b></blockquote>")
    elif bet_type in ["не гол", "не голл"]:
        if dice_value in [1, 2, 3]:
            win_amount = bet_usd * config.cef
            await handle_win(player_id, win_amount)
        else:
            await bot.send_message(config.MAIN_ID, "<blockquote><b>❌ | К сожалению, вы проиграли.</b></blockquote>")
    else:
        await bot.send_message(config.MAIN_ID, "<blockquote><b>💬 | Вы указали неверную игру!\n\n📌 |Напишите администратору @KrasnovWork за возвратом</b></blockquote>")

async def handle_basket(message, bet_usd, bet_comment, player_id):
    footemoji = await bot.send_dice(chat_id=config.MAIN_ID, emoji="🏀")
    foot_value = dice_value.dice.value

    bet_type = bet_comment.split(" ")[1].lower()

    if bet_type in ['забьет', 'забьёт']:
        if foot_value in [4, 5, 6]:
            win_amount = bet_usd * config.cef
            await handle_win(player_id, win_amount)
        else:
            await bot.send_message(config.MAIN_ID, "<blockquote><b>❌ | К сожалению, вы проиграли.</b></blockquote>")
    elif bet_type in ["не забьет", "не забьёт"]:
        if dice_value in [1, 2, 3]:
            win_amount = bet_usd * config.cef
            await handle_win(player_id, win_amount)
        else:
            await bot.send_message(config.MAIN_ID, "<blockquote><b>❌ | К сожалению, вы проиграли.</b></blockquote>")
    else:
        await bot.send_message(config.MAIN_ID, "<blockquote><b>💬 | Вы указали неверную игру!\n\n📌 |Напишите администратору @KrasnovWork за возвратом</b></blockquote>")

async def handle_win(user_id, win_amountt):
    win_amount = round(win_amountt, 2)
    msga = f'''
<b>🎉 Поздравляем, вы выиграли {win_amount}!</b>

<blockquote>Заберите деньги по кнопке ниже!</blockquote>
'''
    try:
        check = await cryptopay.create_check(asset='USDT', amount=win_amount, pin_to_user_id=user_id)
        keyboard = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton(text="🎁 Забрать", url=check.bot_check_url)
        keyboard.add(btn1)
        await bot.send_message(config.MAIN_ID, msga, reply_markup=keyboard)
    except Exception as e:
        await bot.send_message(config.MAIN_ID, f"<b>🎉 Поздравляем, вы выиграли {win_amount}!</b>\n<blockquote>Но в казне недостаточно средств для выплаты. Они будут зачислены вручную администрацией.</blockquote>")
        for admid in config.ADMIN_IDS:
            await bot.send_message(admid, f"<b>АЛОООО СУКА ‼️‼️‼️</b>\nБот не может создать выплату!\n\nЮзер: {user_id}\nСумма: {win_amount}\n\nЛог ошибки: <b>{e}</b>")

@dp.message_handler(commands=['create_invoice'])
async def create_invoice(message: types.Message):
    try:
        amount = float(message.text.split()[1])
        invoice = await cryptopay.create_invoice(asset='USDT', amount=amount)
        await message.reply(f"Создан счет для пополнения казны:\n{invoice.bot_invoice_url}")
    except (IndexError, ValueError):
        await message.reply("Используйте команду в формате: /create_invoice <сумма>")
        
@dp.message_handler(commands=['del_checks'])
async def delete_all_invoices(message: types.Message):
    checks = await cryptopay.get_checks(status='active')
    await message.reply(checks)
    
@dp.message_handler(commands=['pay_money'])
async def cmd_paymoney(message: types.Message):
    if message.from_user.id in config.ADMIN_IDS:
        amount = float(message.text.split(" ")[2])
        id = int(message.text.split(" ")[1])
        await pay_money(amount, id)
        await message.reply("Средства успешно переведены")
    else:
        await message.reply("<b>[⛔] Ошибка!</b>\n\n<blockquote>Вы не администратор!</blockquote>")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)