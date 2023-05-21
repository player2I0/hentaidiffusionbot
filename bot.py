import logging, json, io, base64, random, aiohttp, os, sqlite3, ast, openai
from PIL import Image, PngImagePlugin
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageNotModified
from aiogram.utils.markdown import link

conn = sqlite3.connect('db.db')
c = conn.cursor()

c.execute('''
          CREATE TABLE IF NOT EXISTS users
          ([usr_id] INTEGER PRIMARY KEY, [prompt] TEXT, [seed] INTEGER, [cfg] FLOAT, [steps] INTEGER, [w] INTEGER, [h] INTEGER, [count] INTEGER, [neg] TEXT)
          ''')

API_TOKEN = ''

openai.api_key = ""

sd_txt2img_link = 'http://127.0.0.1:7861/sdapi/v1/txt2img'
sd_img2img_link = 'http://127.0.0.1:7861/sdapi/v1/img2img'
sd_stats_link = 'http://127.0.0.1:7861/sdapi/v1/progress?skip_current_image=false'
sd_skip_link = 'http://127.0.0.1:7861/sdapi/v1/skip'

default = [{"role": "system",
            "content": "User need generate a picture. You should give user a stable diffusion prompt for generating image. At first, user give you his prompt. You should improve this prompt."}]


bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


prompt_b = InlineKeyboardButton('PROMPT', callback_data='prompt')
negative_b = InlineKeyboardButton('NEG PROMPT', callback_data='neg')
seed_b = InlineKeyboardButton('SEED', callback_data='seed')
mode_b = InlineKeyboardButton('MODE', callback_data='mode')
count_b = InlineKeyboardButton('COUNT', callback_data='count')
cfg_b = InlineKeyboardButton('CFG', callback_data='cfg')
size_b = InlineKeyboardButton('SIZE', callback_data='size')
generate_b = InlineKeyboardButton('GENERATE', callback_data='generate')
stats_b = InlineKeyboardButton('STATS', callback_data='stats')
stop_b = InlineKeyboardButton('STOP', callback_data='stop')
kb = InlineKeyboardMarkup().add(prompt_b).add(negative_b, seed_b).add(mode_b, count_b).add(cfg_b, size_b).add(
    generate_b)
kb_on_gen = InlineKeyboardMarkup().add(stats_b, stop_b)
kb_c = InlineKeyboardMarkup().add(InlineKeyboardButton('CANCEL', callback_data='cancel'))

users = {}
msgs = {}
queue = []


def LoadUsers():
    global conn
    global c
    global users
    sqlite_select_query = """SELECT * from users"""
    c.execute(sqlite_select_query)
    records = c.fetchall()
    print("Total rows are:  ", len(records))
    for r in records:
        users[r[0]] = {}
        users[r[0]]['prompt'] = r[1]
        users[r[0]]['seed'] = int(r[2])
        users[r[0]]['cfg'] = float(r[3])
        users[r[0]]['steps'] = int(r[4])
        users[r[0]]['w'] = int(r[5])
        users[r[0]]['h'] = int(r[6])
        users[r[0]]['count'] = int(r[7])
        users[r[0]]['neg'] = str(r[8])
        users[r[0]]['gen'] = False
        users[r[0]]['pre'] = False
        msgs[r[0]] = {}
        msgs[r[0]]['main'] = None
        msgs[r[0]]['stats'] = None


LoadUsers()

class States(StatesGroup):
    prompt = State()
    seed = State()
    modee = State()
    size = State()
    cfg = State()
    s = State()
    neg = State()
    user_id = State()


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('cancel'), state='*')
async def prompt_enter(message: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    logging.info('Cancelling state %r', current_state)
    await w(message.from_user.id, False, None, "cancelled", kb, False)
    await state.finish()


async def w(id, new, msg, text, keyb, d):
    if id not in msgs:
        msgs[id] = {}
        msgs[id]['main'] = None
        msgs[id]['stats'] = None
    if new == True:
        msgs[id]['main'] = await bot.send_message(chat_id=id, text=text, reply_markup=keyb, parse_mode="Markdown",
                                                  disable_web_page_preview=True)
    else:
        if d == False:
            try:
                await msg.edit_text(text=text, reply_markup=keyb)
            except:
                try:
                    await msgs[id]['main'].delete()
                    msgs[id]['main'] = await bot.send_message(chat_id=id, text=text, reply_markup=keyb,
                                                              parse_mode="Markdown", disable_web_page_preview=True)
                except:
                    msgs[id]['main'] = await bot.send_message(chat_id=id, text=text, reply_markup=keyb,
                                                              parse_mode="Markdown", disable_web_page_preview=True)
        else:
            try:
                await msgs[id]['main'].delete()
            except:
                pass
            msgs[id]['main'] = await bot.send_message(chat_id=id, text=text, reply_markup=keyb, parse_mode="Markdown",
                                                      disable_web_page_preview=True)


@dp.message_handler(content_types=types.ContentType.PHOTO)
async def photo_handler(message: types.Message):
    if message.from_user.id in users:
        b = InlineKeyboardButton('image to image', callback_data='img2img')
        k = InlineKeyboardMarkup().add(b)
        if len(users[message.from_user.id]['prompt']) < 800:
            await bot.send_photo(message.from_user.id, message.photo[0]['file_id'],
                                 "prompt:\n`" + users[message.from_user.id]['prompt'] + '`', parse_mode="Markdown",
                                 reply_markup=k)
        else:
            await bot.send_photo(message.from_user.id, message.photo[0]['file_id'],
                                 "too long prompt to be shown\n/prompt to show it", parse_mode="Markdown",
                                 reply_markup=k)
        file_info = await bot.get_file(message.photo[len(message.photo) - 1].file_id)
        byteImgIO = io.BytesIO()
        byteImg = Image.open(await bot.download_file(file_info.file_path))
        byteImg.save(byteImgIO, "PNG")
        byteImgIO.seek(0)
        byteImg = byteImgIO.read()
        users[message.from_user.id]['img'] = str(base64.b64encode(byteImg)).split("b'")[1]
    else:
        await message.reply(text='set prompt with PROMPT first!', reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('img2img'))
async def pin(message: types.CallbackQuery):
    if users[message.from_user.id]['gen'] == False:
        if len(users[message.from_user.id]['prompt']) > 15:
            try:
                await bot.send_message(message.from_user.id,
                                       "generating image...\n/stats - info about generation process\n/stop - stop image generation and send image")
                ee = ''
                if users[message.from_user.id]['steps'] == 35:
                    if users[message.from_user.id]['w'] > 600 or users[callback_query.from_user.id]['h'] > 600:
                        users[message.from_user.id]['steps'] = 15
                        updateUser(message.from_user.id)
                else:
                    e = 'Euler'

                payload = {
                    "prompt": "{}".format(users[message.from_user.id]['prompt']),
                    "seed": "{}".format(users[message.from_user.id]['seed']),
                    "negative_prompt": "EasyNegative, " + str(users[message.from_user.id]['neg']),
                    "steps": int(users[message.from_user.id]['steps']) + 4,
                    "cfg_scale": users[message.from_user.id]['cfg'],
                    "sampler_index": str(e),
                    "enable_hr": False,
                    "width": int(users[message.from_user.id]['w']),
                    "height": int(users[message.from_user.id]['h']),
                    "batch_size": int(users[message.from_user.id]['count']),
                    "init_images": [users[message.from_user.id]['img']]
                }
                queue.append(message.from_user.id)
                users[message.from_user.id]['gen'] = True
                async with aiohttp.ClientSession() as session:
                    async with session.post(sd_img2img_link, json=payload) as response:
                        try:
                            r = await response.json()
                            for i in r['images']:

                                image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
                                num = str(random.random())
                                image.save(num + '.png')
                                img = open(num + '.png', "rb")
                                inn = json.loads(r['info'])
                                p = ''
                                if len(inn['prompt']) <= 700:
                                    p = '`\n\nprompt:\n\n`' + inn['prompt'] + '`'
                                await bot.send_photo(chat_id=f'{message.from_user.id}', photo=img,
                                                     caption="here is your result\n\n" + 'seed: `' + str(
                                                         inn['seed']) + p + f'', parse_mode="Markdown")
                                await message.message.answer(text="what would you like to do next?", reply_markup=kb)
                                users[callback_query.from_user.id]['gen'] = False
                                if queue.count(callback_query.from_user.id) > 0:
                                    queue.remove(callback_query.from_user.id)
                        except Exception as e:
                            await bot.send_message(callback_query.from_user.id,
                                                   'error generating image\n/generate - generate again')
                            users[callback_query.from_user.id]['gen'] = False
                            print(e)
                            queue.remove(callback_query.from_user.id)
            except Exception as e:
                await bot.send_message(callback_query.from_user.id,
                                       'error generating image\nGENERATE - generate again')
                users[callback_query.from_user.id]['gen'] = False
                print(e)
                queue.remove(callback_query.from_user.id)
        else:
            await bot.send_message(callback_query.from_user.id, 'too short prompt!')


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """

    hd = link('Anything V3 model', 'https://huggingface.co/Linaqruf/anything-v3.0')
    await w(message.from_user.id, False, None,
            f"Stable Diffusion Bot using {hd}.\n\n/examples - examples for text prompt", kb, True)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('generate'))
async def generation(message: types.CallbackQuery):
    if message.from_user.id in users:
        if users[message.from_user.id]['gen'] == False:
            if len(users[message.from_user.id]['prompt']) > 15:
                await msgs[message.from_user.id]['main'].edit_text(
                    text="generating image...\nSTATS - info about generation process\nSTOP - stop image generation and send image",
                    reply_markup=kb_on_gen)
                ee = ''
                if users[message.from_user.id]['steps'] == 35:
                    if users[message.from_user.id]['w'] > 600 or users[message.from_user.id]['h'] > 600:
                        users[message.from_user.id]['steps'] = 15
                        updateUser(message.from_user.id)
                    e = 'Euler'
                else:
                    e = 'Euler'
                payload = {
                    "prompt": "{}".format(users[message.from_user.id]['prompt']),
                    "seed": "{}".format(users[message.from_user.id]['seed']),
                    "negative_prompt": "EasyNegative, " + str(users[message.from_user.id]['neg']),
                    "steps": int(users[message.from_user.id]['steps']),
                    "cfg_scale": users[message.from_user.id]['cfg'],
                    "sampler_index": str(e),
                    "enable_hr": False,
                    "width": int(users[message.from_user.id]['w']),
                    "height": int(users[message.from_user.id]['h']),
                    "batch_size": int(users[message.from_user.id]['count'])
                }
                queue.append(message.from_user.id)
                users[message.from_user.id]['gen'] = True
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(sd_txt2img_link, json=payload) as response:
                            try:
                                r = await response.json()
                                for i in r['images']:
                                    image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
                                    num = str(random.random())
                                    image.save(num + '.png')
                                    img = open(num + '.png', "rb")
                                    inn = json.loads(r['info'])
                                    p = ''
                                    if len(inn['prompt']) <= 700:
                                        p = '`\n\nprompt:\n\n`' + inn['prompt'] + '`'
                                    print(message.from_user.id)
                                    await bot.send_photo(chat_id=f'{message.from_user.id}', photo=img,
                                                         caption="here is your result\n\n" + 'seed: `' + str(
                                                             inn['seed']) + p + f'', parse_mode="Markdown")
                                    os.remove(num + '.png')
                                    await w(message.from_user.id, False, None, f"What would you like to do next?", kb,
                                            True)
                                    users[message.from_user.id]['gen'] = False
                                    if queue.count(message.from_user.id) > 0:
                                        queue.remove(message.from_user.id)
                                    try:
                                        await msgs[message.from_user.id]['pre'].delete()
                                    except:
                                        pass
                            except Exception as e:
                                await w(message.from_user.id, False, None, f"Error generating image! Try again", kb,
                                        True)
                                users[message.from_user.id]['gen'] = False
                                print(e)
                                queue.remove(message.from_user.id)
                except Exception as e:
                    await w(message.from_user.id, False, None, f"Error generating image! Try again", kb, True)
                    users[message.from_user.id]['gen'] = False
                    queue.remove(message.from_user.id)
            else:
                await message.answer(text='too short prompt!', show_alert=True)
        else:
            await message.answer(text='image is already generating!', show_alert=True)
    else:
        await message.answer(text='set prompt with PROMPT first!', show_alert=True)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('prompt'))
async def prompt_enter(message: types.CallbackQuery):
    await States.prompt.set()
    if message.from_user.id in users:
        s = users[message.from_user.id]['prompt']
        await message.message.edit_text(text=f"send text prompt\ncurrent prompt:\n\n`{s}`\n\ntype 'random' for random prompt\n\nuse CANCEL to cancel",
                                        parse_mode="Markdown", disable_web_page_preview=True, reply_markup=kb_c)
    else:
        await message.message.edit_text(text="send text prompt\n\nuse CANCEL to cancel", reply_markup=kb_c)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('cfg'))
async def prompt_enter(message: types.CallbackQuery):
    if message.from_user.id in users:
        await States.cfg.set()
        c = str(users[message.from_user.id]['cfg'])
        await message.message.edit_text(
            text=f"send new cfg scale. it needs to be number\ncurrent cfg:\n\n`{c}`\n\nuse CANCEL to cancel",
            parse_mode="Markdown", disable_web_page_preview=True, reply_markup=kb_c)

    else:
        await message.answer(text='set prompt with PROMPT first!', show_alert=True)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('size'))
async def prompt_enter(message: types.CallbackQuery):
    if message.from_user.id in users:
        if users[message.from_user.id]['count'] == 1:
            await States.s.set()
            c = str(users[message.from_user.id]['w']) + "x" + str(users[message.from_user.id]['h'])
            await message.message.edit_text(
                f"send new size of image. it needs to be written in this format: `widthxheight`\ncurrent size:\n\n`{c}`\n\nuse /cancel to cancel",
                parse_mode="Markdown", disable_web_page_preview=True, reply_markup=kb_c)

        else:
            await message.answer(
                f"changing size of image is available only when number of images is set to 1! use COUNT to do that",
                parse_mode="Markdown", show_alert=True)
    else:
        await message.answer(text='set prompt with PROMPT first!', show_alert=True)


@dp.message_handler(state=States.s)
async def process_name(message: types.Message, state: FSMContext):
    s = message.text.split('x')
    w = int(s[0])
    h = int(s[1])
    print(w)
    print(s)
    if w <= 700 and h <= 700:
        await state.finish()
        users[message.from_user.id]['w'] = w
        users[message.from_user.id]['h'] = h
        await w(message.from_user.id, False, None,
                "cfg scale sucessfully set to " + str(users[message.from_user.id]['cfg']), kb, False)
        updateUser(message.from_user.id)
        if w > 600 or h > 600:
            if users[message.from_user.id]['steps'] > 15:
                await msgs[message.from_user.id]['main'].edit_text(
                    text=msgs[message.from_user.id]['main'].text + '\nmode of generation is changed to fast',
                    reply_markup=kb)
                users[message.from_user.id]['steps'] = 15
    else:
        await msgs[message.from_user.id]['main'].edit_text(
            text="width and height of image need to be equal or smaller than 700!\nCANCEL to cancel", reply_markup=kb_c)
    await message.delete()


@dp.message_handler(state=States.cfg)
async def process_name(message: types.Message, state: FSMContext):
    try:
        await state.finish()
        users[message.from_user.id]['cfg'] = float(message.text)
        await w(message.from_user.id, False, None,
                "cfg scale sucessfully set to " + str(users[message.from_user.id]['cfg']), kb, False)

    except ValueError:
        try:
            await msgs[message.from_user.id]['main'].edit_text(
                text=f"cfg scale needs to be a number!\nCANCEL to cancel", reply_markup=kb_c)
        except:
            pass
    await message.delete()


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('mode'))
async def mode_enter(message: types.CallbackQuery):
    if message.from_user.id in users:
        if users[message.from_user.id]['steps'] == 25:
            gg = 'quality'
        elif users[message.from_user.id]['steps'] == 15:
            gg = 'fast'
        elif users[message.from_user.id]['steps'] == 35:
            gg = 'ultra quality'
        await States.modee.set()
        await message.message.edit_text(
            f"select mode of image generation (type it)\n\n`fast` - use fast but worse quality generation mode (about 30 secs)\n`quality` - use slower but more detailed generation mode (about 1 minute)\n`ultra` - use even slower but much more detailed mode\n\ncurrent mode: " + gg + "\n\n/CANCEL to cancel",
            parse_mode="Markdown", reply_markup=kb_c)
    else:
        await message.answer(text='set prompt with PROMPT first!', show_alert=True)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('stats'))
async def stats(message: types.CallbackQuery):
    if message.from_user.id in users:
        if users[message.from_user.id]['gen'] == True:
            if users[message.from_user.id]['pre'] == False:
                if queue.index(message.from_user.id) == 0:
                    msgg = await bot.send_message(chat_id=message.from_user.id, text='generating image info...')
                    users[message.from_user.id]['pre'] = True
                    timeout = aiohttp.ClientTimeout(total=20)
                    try:
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.get(
                                    sd_stats_link) as response:
                                users[message.from_user.id]['pre'] = True
                                r = await response.json()
                                await msgg.delete()
                                try:
                                    try:
                                        image = Image.open(
                                            io.BytesIO(base64.b64decode(r['current_image'].split(",", 1)[0])))
                                        num = str(random.random())
                                        image.save(num + '.png')
                                        img = open(num + '.png', "rb")
                                        await msgs[message.from_user.id]['main'].delete()
                                        msgs[message.from_user.id]['main'] = await bot.send_photo(message.from_user.id,
                                                                                                  img,
                                                                                                  "preview image\n\ncurrent step: " + str(
                                                                                                      r['state'][
                                                                                                          'sampling_step']) + '/' + str(
                                                                                                      r['state'][
                                                                                                          'sampling_steps']) + '\nETA: ' + str(
                                                                                                      int(r[
                                                                                                              'eta_relative'])) + ' sec\nSTATS to refresh',
                                                                                                  reply_markup=kb_on_gen)

                                        users[message.from_user.id]['pre'] = False
                                    except Exception as e:
                                        await message.message.edit_text(
                                            "current step: " + str(r['state']['sampling_step']) + '/' + str(
                                                r['state']['sampling_steps']) + '\nETA: ' + str(
                                                int(r['eta_relative'])) + ' sec\nSTATS to refresh',
                                            reply_markup=kb_on_gen)
                                        users[message.from_user.id]['pre'] = False
                                except Exception as e:
                                    await message.message.edit_text(
                                        'error while generating preview.\nSTATS - try again', reply_markup=kb_on_gen)
                                    users[message.from_user.id]['pre'] = False
                    except Exception as e:
                        await msgs[message.from_user.id]['main'].edit_text(
                            text='error while generating preview.\nSTATS - try again', reply_markup=kb_on_gen)
                        users[message.from_user.id]['pre'] = False
                else:
                    await message.message.edit_text(
                        'you are at ' + str(queue.index(message.from_user.id) + 1) + 'th place in queue',
                        reply_markup=kb_on_gen)
            else:
                await message.answer(text='wait for preview!', show_alert=True)
        else:
            await message.message.edit_text('users in queue: ' + str(len(queue)), reply_markup=kb_on_gen)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('stop'))
async def size_enter(message: types.CallbackQuery):
    if message.from_user.id in users:
        if queue.index(message.from_user.id) == 0:
            timeout = aiohttp.ClientTimeout(total=20)
            try:
                payload = {'_': '_'}
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(sd_skip_link, json=payload) as response:
                        r = await response.json()

            except Exception as e:
                await message.message.reply('error while cancelling image generation', reply_markup=kb_on_gen)
                print(str(e))
            msgs[message.from_user.id]['pre'] = await message.message.reply(
                f"generation of your image cancelled. waiting for generated image so far...", parse_mode="Markdown")
        else:
            await message.answer(text='set prompt with PROMPT first!', show_alert=True)
    else:
        await message.answer(text='set prompt with PROMPT first!', show_alert=True)


@dp.message_handler(state=States.modee)
async def process_name(message: types.Message, state: FSMContext):
    if message.text.find('quality') != -1:
        if users[message.from_user.id]['w'] < 600 and users[message.from_user.id]['h'] < 600:
            await message.reply(f"mode set to:\n\nquality", reply_markup=kb)
            users[message.from_user.id]['steps'] = 25
            if users[message.from_user.id]['count'] == 1:
                users[message.from_user.id]['w'] = 512
                users[message.from_user.id]['h'] = 512
                updateUser(message.from_user.id)
        else:
            await w(message.from_user.id, False, None,
                    "can't set mode to quality because width and height of image need to be smaller than 600", kb,
                    False)
        await state.finish()
    elif message.text.find('ultra') != -1:
        await w(message.from_user.id, False, None, "mode set to:\n\nultra quality", kb, False)
        users[message.from_user.id]['steps'] = 35
        await state.finish()
    elif message.text.find('fast') != -1:
        await w(message.from_user.id, False, None, "mode set to:\n\nfast", kb, False)
        users[message.from_user.id]['steps'] = 15
        await state.finish()
    else:
        try:
            await msgs[message.from_user.id]['main'].edit_text(text=f"type actual mode\n\nCANCEL to cancel",
                                                               reply_markup=kb_c)
        except:
            pass
    await message.delete()


@dp.message_handler(commands=['examples'])
async def seed_enter(message: types.Message):
    hd = link('this page', 'https://github.com/Delcos/Hentai-Diffusion')
    await message.answer(
        f"examples for text prompt\n\nMonika from DDLC (from {hd}):\n" + "`best quality, {{{nsfw}}}, {{{masterpiece}}}, 1girl, monika (doki doki literature club, (breasts:0.984), (brown hair:0.989), (cleavage:0.586), (collarbone:0.746), (eyebrows visible through hair:0.732), (green eyes:0.944), (long hair:0.982), (ponytail:0.741), plump, wide hips, ((white_ribbon)), jeans, t-shirt, trembling, embarrassed, (autumn leaves, autumn), cowboy shot, outdoors, (cropped legs), blurry background`\n\nYuri from DDLC:\n`best quality, (1girl), anime, (a standing yuri from doki doki literature club), (mature), slim, (tall), (wide hips), white knee-high socks, brown sweater vest, ((warm dark gray long sleeve blazer)) fully buttoned and untucked with buttons, white shirt under blazer slightly unbuttoned at the collar and tucked, trembling, cute, embarassed, autumn leaves, autumn, cowboy shot, outdoors, (cropped legs), blurry background, (breasts:1.5), (long dark purple hair), (light purple eyes:0.1), (thin red ribbon on chest), dark blue skirt, ((hands behind back)), (very slight embarassed smile)` \n\nNSFW #1:\n`An extremely detailed illustration of a girl, big boobs, (thin), ((torn stockings)), black stockings, white wall, naked, (white socks), (((uncensored))), hair ornament ribbon, brown hair, long hair, big smile, pink nipples, (((exposed nipples))), kneeling, legs spread, bright lighting, ((lifting shirt up)), full body shot, blackcouch, ((smooth skin)), (detailed shadows), HD wallpaper, UHD image, best quality, extremely detailed, ((masterpiece)), (anime picture)`",
        parse_mode="Markdown", disable_web_page_preview=True, reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('seed'))
async def mode_enter(message: types.CallbackQuery):
    if message.from_user.id in users:
        await States.seed.set()
        await message.message.edit_text(
            f"type seed you want to use for image generation\ntype -1 if you want to use random seed\n\ncurrent seed: `" + str(
                users[message.from_user.id]['seed']) + "`\n\nCANCEL to cancel", parse_mode="Markdown",
            disable_web_page_preview=True, reply_markup=kb_c)
    else:
        await message.answer(text='set prompt with PROMPT first!', show_alert=True)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('count'))
async def mode_enter(message: types.CallbackQuery):
    if message.from_user.id in users:
        await States.size.set()
        await message.message.edit_text(
            f"type how many images need to be generated. note that the more images, the smaller their size",
            parse_mode="Markdown", reply_markup=kb_c)
    else:
        await message.answer(text='set prompt with PROMPT first!', show_alert=True)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('neg'))
async def mode_enter(message: types.CallbackQuery):
    if message.from_user.id in users:
        await States.neg.set()
        n = str(users[message.from_user.id]['neg'])
        await message.message.edit_text(
            f"type your negative prompt. type `none` if you don't want it. current negative prompt:\n\n`{n}`\n\nCANCEL to cancel",
            parse_mode="Markdown", reply_markup=kb_c)
    else:
        await message.answer(text='set prompt with PROMPT first!', show_alert=True)


@dp.message_handler(state=States.neg)
async def process_name(message: types.Message, state: FSMContext):
    if message.text == '/cancel':
        await state.finish()
        await w(message.from_user.id, False, None, "cancelled", kb, False)
    else:
        users[message.from_user.id]['neg'] = str(message.text)
        updateUser(message.from_user.id)
        await w(message.from_user.id, False, None, f"negative prompt was set to: \n\n`{message.text}`", kb, False)
        await state.finish()
    await message.delete()


@dp.message_handler(state=States.size)
async def process_name(message: types.Message, state: FSMContext):
    if message.text.isdigit() is True:
        siz = 0
        if int(message.text) != 1:
            siz = int(800 / int(message.text))
        else:
            siz = 512
        if int(message.text) > 0 and int(message.text) < 10:
            users[message.from_user.id]['count'] = int(message.text)
            users[message.from_user.id]['w'] = int(siz)
            users[message.from_user.id]['h'] = int(siz)
            await w(message.from_user.id, False, None,
                    f'number of images to be generated: {int(message.text)}\ntheir size: {siz}x{siz}', kb, False)
            await state.finish()
            updateUser(message.from_user.id)
        else:
            try:
                await msgs[message.from_user.id]['main'].edit_text(
                    text=f"type number between 1 and 10\n\nCANCEL to cancel", reply_markup=kb_c)
            except:
                pass
    else:
        await state.finish()
        await w(message.from_user.id, False, None, f'cancelled', kb, False)
    await message.delete()


@dp.message_handler(state=States.seed)
async def process_name(message: types.Message, state: FSMContext):
    if message.text.isdigit() is True:
        await state.finish()
        await w(message.from_user.id, False, None, f"seed set to:\n\n{message.text}", kb, False)
        users[message.from_user.id]['seed'] = int(message.text)
        updateUser(message.from_user.id)
    else:
        if message.text == '-1':
            await state.finish()
            await w(message.from_user.id, False, None, f"seed set to:\n\n{message.text}", kb, False)
            users[message.from_user.id]['seed'] = int(message.text)
            updateUser(message.from_user.id)
        else:
            try:
                await msgs[message.from_user.id]['main'].edit_text(
                    text=f"seed needs to be a number! type seed again without any letters\n\nCANCEL to cancel",
                    reply_markup=kb_c)
            except:
                pass
    await message.delete()


@dp.message_handler(state=States.prompt)
async def process_name(message: types.Message, state: FSMContext):
    await state.finish()
    if message.from_user.id in users:
        # Random mode
        if message.text == "random":
            sqlite_select_query = """SELECT * from users"""
            records = c.execute(sqlite_select_query)
            records = len(c.fetchall())
            users[message.from_user.id]['prompt'] = c.execute(f"SELECT prompt FROM users ORDER BY RANDOM() LIMIT {records}").fetchone()
            users[message.from_user.id]['prompt'] = users[message.from_user.id]['prompt'][0]
            await w(message.from_user.id, False, None, f"prompt set to:\n\n{users[message.from_user.id]['prompt']}", kb, False)
            updateUser(int(message.from_user.id))
        else:
            users[message.from_user.id]['prompt'] = message.text
            await w(message.from_user.id, False, None, f"prompt set to:\n\n{users[message.from_user.id]['prompt']}", kb, False)
            updateUser(message.from_user.id)
    else:
        create_user(message.from_user.id, message.text)
    await message.delete()



@dp.message_handler(content_types=["text"])
async def gpt_working(message: types.Message):
    gpt_prompt = default
    gpt_prompt.append({"role": "user", "content": f"{message.text}"})
    try:
        gpt_prompt = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=gpt_prompt)
        gpt_prompt = gpt_prompt["choices"][0]["message"]["content"]
        await message.answer(gpt_prompt, reply_markup=kb)
    except Exception:
        await message.answer("error generating response")
    gpt_prompt = []


def create_user(user: int, prompt: str):
    global conn
    users[user] = {}
    users[user]['prompt'] = prompt
    users[user]['seed'] = -1
    users[user]['cfg'] = 11.5
    users[user]['steps'] = 15
    users[user]['gen'] = False
    users[user]['pre'] = False
    users[user]['w'] = 512
    users[user]['h'] = 512
    users[user]['count'] = 1
    users[user]['neg'] = ""
    msgs[user] = {}
    msgs[user]['main'] = None
    msgs[user]['stats'] = None
    sqlite_insert_with_param = '''
          INSERT INTO users (usr_id, prompt, seed, cfg, steps, w, h, count, neg)

                VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?);
          '''

    data_tuple = (user, prompt, -1, 11.5, 15, 512, 512, 1, '')
    c.execute(sqlite_insert_with_param, data_tuple)
    conn.commit()


def updateUser(user: int):
    global conn
    global c
    sqlite_update_query = """Update users set prompt = ?, seed = ?, cfg = ?, steps = ?, w = ?, h = ?, count = ?, neg = ? where usr_id = ?"""
    columnValues = (
        users[user]['prompt'], users[user]['seed'], users[user]['cfg'], users[user]['steps'], users[user]['h'],
        users[user]['w'], users[user]['count'], users[user]['neg'], user)
    c.execute(sqlite_update_query, columnValues)
    conn.commit()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
