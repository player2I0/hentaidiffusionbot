import logging
import json
import requests
import io
import base64
import random
import aiohttp
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
import os


API_TOKEN = '5808775042:AAHeGa1cwfG8GL-ty15bA4EwMrJgEyXgsEI'

# Configure logging
logging.basicConfig(level=logging.INFO)
users = {}
queue = []

def SaveUsers(path):
    f = open(path, "w")
    s = ''
    for i in users.keys():
        s = s + str(i) + '::~~::' + users[i]['prompt'] + '::~~::' + str(users[i]['seed']) + '::~~::' + str(users[i]['cfg']) + '::~~::' + str(users[i]['steps']) + '::~~::' + str(users[i]['w']) + '::~~::' + str(users[i]['h']) + '::~~::' + str(users[i]['count']) + '\n'
    f.write(s)
    f.close()
    
def LoadUsers(path):
    global users
    if not os.path.exists(path):
        f = open(path, "x")
        f.close()
    else:
        f = open(path, "r")
        l = f.readlines()
        for i in l:
            items = i.split("::~~::")
            
            users[int(items[0])] = {}
            #users[user]['prompt'] = prompt
            #users[user]['seed'] = -1
            #users[user]['cfg'] = 11.5
            #users[user]['steps'] = 25
            #users[user]['gen'] = False
            #users[user]['pre'] = False
            #users[user]['w'] = 512
            #users[user]['h'] = 512
            #users[user]['count'] = 1
            users[int(items[0])]['prompt'] = items[1]
            users[int(items[0])]['seed'] = int(items[2])
            users[int(items[0])]['cfg'] = float(items[3])
            users[int(items[0])]['steps'] = int(items[4])
            users[int(items[0])]['gen'] = False
            users[int(items[0])]['pre'] = False
            users[int(items[0])]['w'] = int(items[5])
            users[int(items[0])]['h'] = int(items[6])
            users[int(items[0])]['count'] = int(items[7])
        f.close()

LoadUsers("C:\\Users\\biomusor\\Downloads\\diff-bot\\users.txt")

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

k = '\n\n/prompt - change prompt of image\n/seed - change seed of image\n/mode - change generation mode\n/count - number of images to generate\n/generate - generate image'

class Prompt(StatesGroup):
    prompt = State()
class Seed(StatesGroup):
    seed = State()
class Modee(StatesGroup):
    modee = State()
class Size(StatesGroup):
    size = State()

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    
    #inline_btn_1 = InlineKeyboardButton('set prompt', callback_data='nigga')
    #inline_kb1 = InlineKeyboardMarkup().add(inline_btn_1)

    #await message.reply("generating image...", reply_markup=inline_kb1)
    hd = link('Anything V3 model', 'https://huggingface.co/Linaqruf/anything-v3.0')
    await message.reply(f"Stable Diffusion Bot using {hd}. Start here:{k}\n\n/examples - examples for text prompt", parse_mode= "Markdown", disable_web_page_preview= True)

@dp.message_handler(commands=['generate'])
async def prompt_enter(message: types.Message):
    print(users)
    if message.from_user.id in users:
        if users[message.from_user.id]['gen'] == False:
            if len(users[message.from_user.id]['prompt']) > 15:
                await message.reply("generating image...\nyou can view info about generation process using /stats")
                ee = ''
                if users[message.from_user.id]['steps'] == 35:
                    e = 'Euler'
                else:
                    e = 'Euler'
                payload = {
                    "prompt": "{}".format(users[message.from_user.id]['prompt']),
                    "seed": "{}".format(users[message.from_user.id]['seed']),
                    "negative_prompt": "(((deformed))), blurry, bad anatomy, disfigured, poorly drawn face, mutation, mutated, (extra_limb), (ugly), (poorly drawn hands), fused fingers, messy drawing, broken legs censor, censored, censor_bar, multiple breasts, (mutated hands and fingers:1.5), (long body :1.3), (mutation, poorly drawn :1.2), black-white, bad anatomy, liquid body, liquidtongue, disfigured, malformed, mutated, anatomical nonsense, text font ui, error, malformed hands, long neck, blurred, lowers, low res, bad anatomy, bad proportions, bad shadow, uncoordinated body, unnatural body, fused breasts, bad breasts, huge breasts, poorly drawn breasts, extra breasts, liquid breasts, heavy breasts, missingbreasts, huge haunch, huge thighs, huge calf, bad hands, fused hand, missing hand, disappearing arms, disappearing thigh, disappearing calf, disappearing legs, fusedears, bad ears, poorly drawn ears, extra ears, liquid ears, heavy ears, missing ears, fused animal ears, bad animal ears, poorly drawn animal ears, extra animal ears, liquidanimal ears, heavy animal ears, missing animal ears, text, ui, error, missing fingers, missing limb, fused fingers, one hand with more than 5 fingers, one hand with less than5 fingers, one hand with more than 5 digit, one hand with less than 5 digit, extra digit, fewer digits, fused digit, missing digit, bad digit, liquid digit, colorful tongue, blacktongue, cropped, watermark, username, blurry, JPEG artifacts, signature, 3D, 3D game, 3D game scene, 3D character, malformed feet, extra feet, bad feet, poorly drawnfeet, fused feet, missing feet, extra shoes, bad shoes, fused shoes, more than two shoes, poorly drawn shoes, bad gloves, poorly drawn gloves, fused gloves, bad cum, poorly drawn cum, fused cum, bad hairs, poorly drawn hairs, fused hairs, big muscles, ugly, bad face, fused face, poorly drawn face, cloned face, big face, long face, badeyes, fused eyes poorly drawn eyes, extra eyes, malformed limbs, more than 2 nipples, missing nipples, different nipples, fused nipples, bad nipples, poorly drawnnipples, black nipples, colorful nipples, gross proportions. short arm, (((missing arms))), missing thighs, missing calf, missing legs, mutation, duplicate, morbid, mutilated, poorly drawn hands, more than 1 left hand, more than 1 right hand, deformed, (blurry), disfigured, missing legs, extra arms, extra thighs, more than 2 thighs, extra calf,fused calf, extra legs, bad knee, extra knee, more than 2 legs, bad tails, bad mouth, fused mouth, poorly drawn mouth, bad tongue, tongue within mouth, too longtongue, black tongue, big mouth, cracked mouth, bad mouth, dirty face, dirty teeth, dirty pantie, fused pantie, poorly drawn pantie, fused cloth, poorly drawn cloth, badpantie, yellow teeth, thick lips, bad camel toe, colorful camel toe, bad asshole, poorly drawn asshole, fused asshole, missing asshole, bad anus, bad pussy, bad crotch, badcrotch seam, fused anus, fused pussy, fused anus, fused crotch, poorly drawn crotch, fused seam, poorly drawn anus, poorly drawn pussy, poorly drawn crotch, poorlydrawn crotch seam, bad thigh gap, missing thigh gap, fused thigh gap, liquid thigh gap, poorly drawn thigh gap, poorly drawn anus, bad collarbone, fused collarbone, missing collarbone, liquid collarbone, strong girl, obesity, worst quality, low quality, normal quality, liquid tentacles, bad tentacles, poorly drawn tentacles, split tentacles, fused tentacles, missing clit, bad clit, fused clit, colorful clit, black clit, liquid clit, QR code, bar code, censored, safety panties, safety knickers, beard, furry, pony, pubic hair, mosaic, futa, testis, (((deformed))), blurry, bad anatomy, disfigured, poorly drawn face, mutation, mutated, (extra_limb), (ugly), (poorly drawn hands), fused fingers, messy drawing, broken legs censor, censored, censor_bar, multiple breasts, (mutated hands and fingers:1.5), (long body :1.3), (mutation, poorly drawn :1.2), black-white, bad anatomy, liquid body, liquidtongue, disfigured, malformed, mutated, anatomical nonsense, text font ui, error, malformed hands, long neck, blurred, lowers, low res, bad anatomy, bad proportions, bad shadow, uncoordinated body, unnatural body, fused breasts, bad breasts, huge breasts, poorly drawn breasts, extra breasts, liquid breasts, heavy breasts, missingbreasts, huge haunch, huge thighs, huge calf, bad hands, fused hand, missing hand, disappearing arms, disappearing thigh, disappearing calf, disappearing legs, fusedears, bad ears, poorly drawn ears, extra ears, liquid ears, heavy ears, missing ears, fused animal ears, bad animal ears, poorly drawn animal ears, extra animal ears, liquidanimal ears, heavy animal ears, missing animal ears, text, ui, error, missing fingers, missing limb, fused fingers, one hand with more than 5 fingers, one hand with less than5 fingers, one hand with more than 5 digit, one hand with less than 5 digit, extra digit, fewer digits, fused digit, missing digit, bad digit, liquid digit, colorful tongue, blacktongue, cropped, watermark, username, blurry, JPEG artifacts, signature, 3D, 3D game, 3D game scene, 3D character, malformed feet, extra feet, bad feet, poorly drawnfeet, fused feet, missing feet, extra shoes, bad shoes, fused shoes, more than two shoes, poorly drawn shoes, bad gloves, poorly drawn gloves, fused gloves, bad cum, poorly drawn cum, fused cum, bad hairs, poorly drawn hairs, fused hairs, big muscles, ugly, bad face, fused face, poorly drawn face, cloned face, big face, long face, badeyes, fused eyes poorly drawn eyes, extra eyes, malformed limbs, more than 2 nipples, missing nipples, different nipples, fused nipples, bad nipples, poorly drawnnipples, black nipples, colorful nipples, gross proportions. short arm, (((missing arms))), missing thighs, missing calf, missing legs, mutation, duplicate, morbid, mutilated, poorly drawn hands, more than 1 left hand, more than 1 right hand, deformed, (blurry), disfigured, missing legs, extra arms, extra thighs, more than 2 thighs, extra calf,fused calf, extra legs, bad knee, extra knee, more than 2 legs, bad tails, bad mouth, fused mouth, poorly drawn mouth, bad tongue, tongue within mouth, too longtongue, black tongue, big mouth, cracked mouth, bad mouth, dirty face, dirty teeth, dirty pantie, fused pantie, poorly drawn pantie, fused cloth, poorly drawn cloth, badpantie, yellow teeth, thick lips, bad camel toe, colorful camel toe, bad asshole, poorly drawn asshole, fused asshole, missing asshole, bad anus, bad pussy, bad crotch, badcrotch seam, fused anus, fused pussy, fused anus, fused crotch, poorly drawn crotch, fused seam, poorly drawn anus, poorly drawn pussy, poorly drawn crotch, poorlydrawn crotch seam, bad thigh gap, missing thigh gap, fused thigh gap, liquid thigh gap, poorly drawn thigh gap, poorly drawn anus, bad collarbone, fused collarbone, missing collarbone, liquid collarbone, strong girl, obesity, worst quality, low quality, normal quality, liquid tentacles, bad tentacles, poorly drawn tentacles, split tentacles, fused tentacles, missing clit, bad clit, fused clit, colorful clit, black clit, liquid clit, QR code, bar code, censored, safety panties, safety knickers, beard, furry, pony, pubic hair, mosaic, futa, testis",
                    "steps": int(users[message.from_user.id]['steps']),
                    "cfg_scale": 7,
                    "sampler_index": str(e),
                    "enable_hr": False,
                    "width": int(users[message.from_user.id]['w']),
                    "height": int(users[message.from_user.id]['h']),
                    "batch_size": int(users[message.from_user.id]['count'])
                }
                queue.append(message.from_user.id)
                print(queue)
                users[message.from_user.id]['gen'] = True
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(f'http://127.0.0.1:7860/sdapi/v1/txt2img', json=payload) as response:
                            inf = ''
                            try:
                                r = await response.json()
                                info = await response.text()
                                info = info.split(", ")
                                #print(info)
                                
                                for i in r['images']:
                                    image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))
                                    num = str(random.random())
                                    image.save(num + '.png')
                                    img=open(num + '.png', "rb")
                                    
                                    s_count = 1
                                    for i in info:
                                        if i.find('Seed') != -1 and s_count !=0:
                                            inf = inf + i
                                            s_count = 0
                                    users[message.from_user.id]['img'] = img
                                    await bot.send_photo(message.from_user.id, img, "here is your result\n\n" + inf + f'{k}')
                                    users[message.from_user.id]['gen'] = False
                                    if queue.count(message.from_user.id) > 0:
                                        queue.remove(message.from_user.id)
                            except Exception as e:
                                await message.reply('error generating image\ntrying to send image again...')
                                #users[message.from_user.id]['gen'] = False
                                try:
                                    await bot.send_photo(message.from_user.id, users[message.from_user.id]['img'], "here is your result\n\n" + inf + f'{k}')
                                    users[message.from_user.id]['gen'] = False
                                except Exception as e:
                                    await message.reply("can't send your image\n/generate - generate again")
                                    users[message.from_user.id]['gen'] = False
                                queue.remove(message.from_user.id)
                                print(e)
                except Exception as e:
                    await message.reply('error generating image\n/generate - try again')
                    users[message.from_user.id]['gen'] = False
                    queue.remove(message.from_user.id)
            else:
                await message.reply("too short prompt!")
        else:
            await message.reply("image is already generating!")
    else:
        await message.reply("you didn't set prompt\nuse /prompt")

@dp.message_handler(commands=['prompt'])
async def prompt_enter(message: types.Message):
    await Prompt.prompt.set()
    if message.from_user.id in users:
        s = users[message.from_user.id]['prompt']
        await message.reply(f"send text prompt\ncurrent prompt:\n\n`{s}`\n\nuse /cancel to cancel", parse_mode= "Markdown", disable_web_page_preview= True)
    else:
        await message.reply("send text prompt\n\nuse /cancel to cancel")
        
@dp.message_handler(commands=['mode'])
async def mode_enter(message: types.Message):
    if message.from_user.id in users:
        if users[message.from_user.id]['steps'] == 25:
            
            gg = 'quality'
        elif users[message.from_user.id]['steps'] == 15:
            if users[message.from_user.id]['count'] == 1:
                users[message.from_user.id]['w'] = 512
                users[message.from_user.id]['h'] = 512
            gg = 'fast'
        elif users[message.from_user.id]['steps'] == 35:
            if users[message.from_user.id]['count'] == 1:
                users[message.from_user.id]['w'] = 630
                users[message.from_user.id]['h'] = 630
            gg = 'ultra quality'
        await Modee.modee.set()
        await message.reply(f"select mode of image generation (type it)\n\n`fast` - use fast but worse quality generation mode (about 30 secs)\n`quality` - use slower but more detailed generation mode (about 1 minute)\n`ultra quality` (currently unavailable) - use even slower but much more detailed mode\n\ncurrent mode: " + gg + "\n\n/cancel to cancel", parse_mode= "Markdown")
    else:
        await message.reply('set prompt with /prompt first!')
        
@dp.message_handler(commands=['stats'])
async def stats(message: types.Message):
    print(users[message.from_user.id]['pre'])
    if message.from_user.id in users:
        if users[message.from_user.id]['gen'] == True:
            if users[message.from_user.id]['pre'] == False:
                if queue.index(message.from_user.id) == 0:
                    await message.reply('generating image info...')
                    users[message.from_user.id]['pre'] = True
                    timeout = aiohttp.ClientTimeout(total=20)
                    try:
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.get(f'http://127.0.0.1:7860/sdapi/v1/progress?skip_current_image=false') as response:
                                users[message.from_user.id]['pre'] = True
                                r = await response.json()
                                try:
                                    try:
                                        image = Image.open(io.BytesIO(base64.b64decode(r['current_image'].split(",",1)[0])))
                                        num = str(random.random())
                                        image.save(num + '.png')
                                        img=open(num + '.png', "rb")
                                        await bot.send_photo(message.from_user.id, img, "preview image\n\ncurrent step: " + str(r['state']['sampling_step']) + '/' + str(r['state']['sampling_steps']) + '\nETA: ' + str(int(r['eta_relative'])) + ' sec\n/stats to refresh')
                                        os.remove(num + '.png')
                                    except Exception as e:
                                        await message.reply("current step: " + str(r['state']['sampling_step']) + '/' + str(r['state']['sampling_steps']) + '\nETA: ' + str(int(r['eta_relative'])) + ' sec\n/stats to refresh')
                                    users[message.from_user.id]['pre'] = False
                                except Exception as e:
                                    await message.reply('error while generating preview.\n/stats - try again')
                                    users[message.from_user.id]['pre'] = False
                    except Exception as e:
                        await message.reply('error while generating preview.\n/stats - try again')
                        users[message.from_user.id]['pre'] = False
                else:
                    await message.reply('you are at ' + str(queue.index(message.from_user.id)+1) + 'th place in queue')
            else:
                await message.reply('wait for preview!')
        

@dp.message_handler(state=Modee.modee)
async def process_name(message: types.Message, state: FSMContext):
    if message.text.find('quality') != -1:
        await message.reply(f"mode set to:\n\nquality{k}")
        users[message.from_user.id]['steps'] = 25
        if users[message.from_user.id]['count'] == 1:
            users[message.from_user.id]['w'] = 512
            users[message.from_user.id]['h'] = 512
            SaveUsers("C:\\Users\\biomusor\\Downloads\\diff-bot\\users.txt")
        await state.finish()
    elif message.text.find('fast') != -1:
        await message.reply(f"mode set to:\n\nfast{k}")
        users[message.from_user.id]['steps'] = 15
        if users[message.from_user.id]['count'] == 1:
            users[message.from_user.id]['w'] = 512
            users[message.from_user.id]['h'] = 512
            SaveUsers("C:\\Users\\biomusor\\Downloads\\diff-bot\\users.txt")
        await state.finish()
    elif message.text == '/cancel':
        await state.finish()
        await message.reply(f'cancelled{k}', reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.reply(f"type actual mode\n\n/cancel to cancel")

@dp.message_handler(commands=['examples'])
async def seed_enter(message: types.Message):
    hd = link('this page', 'https://github.com/Delcos/Hentai-Diffusion')
    await message.reply(f"examples for text prompt\n\nMonika from DDLC (from {hd}):\n" + "`best quality, {{{nsfw}}}, {{{masterpiece}}}, 1girl, monika (doki doki literature club, (breasts:0.984), (brown hair:0.989), (cleavage:0.586), (collarbone:0.746), (eyebrows visible through hair:0.732), (green eyes:0.944), (long hair:0.982), (ponytail:0.741), plump, wide hips, ((white_ribbon)), jeans, t-shirt, trembling, embarrassed, (autumn leaves, autumn), cowboy shot, outdoors, (cropped legs), blurry background`\n\nYuri from DDLC:\n`best quality, (1girl), anime, (a standing yuri from doki doki literature club), (mature), slim, (tall), (wide hips), white knee-high socks, brown sweater vest, ((warm dark gray long sleeve blazer)) fully buttoned and untucked with buttons, white shirt under blazer slightly unbuttoned at the collar and tucked, trembling, cute, embarassed, autumn leaves, autumn, cowboy shot, outdoors, (cropped legs), blurry background, (breasts:1.5), (long dark purple hair), (light purple eyes:0.1), (thin red ribbon on chest), dark blue skirt, ((hands behind back)), (very slight embarassed smile)`", parse_mode= "Markdown", disable_web_page_preview= True)

@dp.message_handler(commands=['seed'])
async def seed_enter(message: types.Message):
    if message.from_user.id in users:
        await Seed.seed.set()
        await message.reply(f"type seed you want to use for image generation\ntype -1 if you want to use random seed\n\ncurrent seed: `" + str(users[message.from_user.id]['seed']) + "`\n\n/cancel to cancel", parse_mode= "Markdown", disable_web_page_preview= True)
    else:
        await message.reply('set prompt with /prompt first!')
        
@dp.message_handler(commands=['count'])
async def size_enter(message: types.Message):
    if message.from_user.id in users:
        await Size.size.set()
        await message.reply(f"type how many images needs to be generated. note that the more images, the smaller their size", parse_mode= "Markdown")
    else:
        await message.reply('set prompt with /prompt first!')
        
@dp.message_handler(state=Size.size)
async def process_name(message: types.Message, state: FSMContext):
    if message.text.isdigit() is True:
        siz = 0
        if int(message.text) != 1:
            siz = int(800/int(message.text))
        else:
            if users[message.from_user.id]['steps'] == 35:
                siz = 630
            else:
                siz = 512
        if int(message.text) > 0 and int(message.text) < 10:
            users[message.from_user.id]['count'] = int(message.text)
            users[message.from_user.id]['w'] = int(siz)
            users[message.from_user.id]['h'] = int(siz)
            await message.reply(f'number of images to be generated: {int(message.text)}\ntheir size: {siz}x{siz}{k}', reply_markup=types.ReplyKeyboardRemove())
            await state.finish()
            SaveUsers("C:\\Users\\biomusor\\Downloads\\diff-bot\\users.txt")
        else:
            await message.reply(f"type number between 1 and 10\n\n/cancel to cancel")
    else:
        if message.text == '/cancel':
            await state.finish()
            await message.reply(f'cancelled{k}', reply_markup=types.ReplyKeyboardRemove())
        else:
            await message.reply(f"type actual number\n\n/cancel to cancel")
    
@dp.message_handler(state=Seed.seed)
async def process_name(message: types.Message, state: FSMContext):
    if message.text.isdigit() is True:
        await state.finish()
        await message.reply(f"seed set to:\n\n{message.text}{k}")
        users[message.from_user.id]['seed'] = int(message.text)
        SaveUsers("C:\\Users\\biomusor\\Downloads\\diff-bot\\users.txt")
    else:
        if message.text == '-1':
            await state.finish()
            await message.reply(f"seed set to:\n\n{message.text}{k}")
            users[message.from_user.id]['seed'] = int(message.text)
        elif message.text == '/cancel':
            await state.finish()
            await message.reply(f'cancelled{k}', reply_markup=types.ReplyKeyboardRemove())
        else:
            await message.reply(f"seed needs to be a number! type seed again without any letters\n\n/cancel to cancel")

@dp.message_handler(state='*', commands='cancel')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply(f'cancelled{k}', reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(state=Prompt.prompt)
async def process_name(message: types.Message, state: FSMContext):
    await state.finish()
    await message.reply(f"prompt set to:\n\n{message.text}{k}")
    if message.from_user.id in users:
        #users.update({message.from_user.id: message.text})
        users[message.from_user.id]['prompt'] = message.text
        SaveUsers("C:\\Users\\biomusor\\Downloads\\diff-bot\\users.txt")
    else:
        #users.update({message.from_user.id: message.text})
        create_user(message.from_user.id, message.text)
    print(users)

def create_user(user: int, prompt: str):
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
    SaveUsers("C:\\Users\\biomusor\\Downloads\\diff-bot\\users.txt")
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

