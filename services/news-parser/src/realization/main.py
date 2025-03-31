from parser import *

import time


while True:
    channels_data = load_channels()
    result = client.loop.run_until_complete(single_call(channels_data))
    # TODO сохранение для результата, вызов моделей для обработки, сохранение в БД

    time.sleep(300)