import base64
import json

import requests

from image import ImageProcessor
from PIL import Image

url = "http://127.0.0.1:7860"

avoid_nsfw_prompt = '{nsfw, nude}, '
# base_prompt = 'masterpiece, best quality,(SFW), '
override_settings = {
    "CLIP_stop_at_last_layers": 2
}
base_prompt = 'masterpiece, best quality,'
# base_prompt = 'best quality, masterpiece, (photorealistic:1.4)'
base_negative = 'EasyNegative, negative_hand-neg,'
# base_negative = 'easynegative,ng_deepnegative_v1_75t,(worst quality:2),(low quality:2),(normal quality:2),lowres,bad anatomy,bad hands,normal quality,((monochrome)),((grayscale)),((watermark))'

add_detailer = False

available_size = {
    "portrait": (512, 768),
    "landscape": (768, 512),
    "square": (512, 512)
}


class SdApi:
    def __init__(self):
        self.image_processor = ImageProcessor(20)
        self.last_gen_info = None

    def get_image(self, params):
        """
        :param params:
        :return: A list containing the path of generated images
        """

        if params['type'] == 'text2img':
            return self.get_text2img(params)
        elif params['type'] == 'img2img':
            return self.get_img2img(params)

    def get_text2img(self, params):
        prompt = params['prompt']

        enable_hr = True

        size = available_size['square']
        width = size[0]
        height = size[1]

        hr_scale = 1
        if params['res'] == 1:
            hr_scale = 1.5
        elif params['res'] == 2:
            hr_scale = 2
        else:
            enable_hr = False

        batch_size = 1
        if params['multi']:
            if params['res'] == 1:
                batch_size = 2
            elif params['res'] == 2:
                batch_size = 2
            else:
                batch_size = 4

        negative = avoid_nsfw_prompt + base_negative
        if params['true']:
            negative = base_negative

        payload = {
            "prompt": base_prompt + prompt,
            "negative_prompt": negative,
            "steps": 27,
            "sampler_name": "DPM++ SDE Karras",
            "batch_size": batch_size,
            "width": width,
            "height": height,
            "enable_hr": enable_hr,
            "denoising_strength": 0.3,
            "hr_scale": hr_scale,
            "hr_second_pass_steps": 22,
            "hr_upscaler": "R-ESRGAN 4x+",
            "cfg_scale": 7,
            "override_settings": override_settings,
        }

        if add_detailer:
            payload['alwayson_scripts'] = {
                "ADetailer": {
                    "args": [
                        {
                            'ad_model': 'face_yolov8s.pt',
                        }
                    ]
                }
            }

        response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload).json()

        print(response['parameters'])

        self.last_gen_info = json.loads(response['info'])

        return self.image_processor.handle_images(response, base_prompt + prompt)

    def get_img2img(self, params):
        # Preprocess input Image
        image_path = params['img_path']
        with open(image_path, 'rb') as file:
            image_data = file.read()
        encoded_image = base64.b64encode(image_data).decode('utf-8')

        raw_width, raw_height = Image.open(image_path).size

        if raw_width > 768:
            raise Exception('图太大力，请不要选择高分辨率图片')

        hr_scale = 1
        if params['res'] == 1:
            hr_scale = 1.5
        elif params['res'] == 2:
            hr_scale = 2
        hr_script = {
            "script_name": "SD upscale",
            "script_args": [
                "", 64, "4x-UltraSharp", hr_scale
            ]
        }

        denoising_strength = 0.3
        if params['redraw_strength'] == 2:
            denoising_strength = 0.5
        elif params['redraw_strength'] == 3:
            denoising_strength = 0.75

        payload = {
            "init_images": [encoded_image],
            "prompt": params['prompt'],
            "negative_prompt": base_negative,
            "steps": 27,
            "sampler_name": "DPM++ SDE Karras",
            "batch_size": 3,
            "width": raw_width * hr_scale,
            "height": raw_height * hr_scale,
            "denoising_strength": denoising_strength,
            "cfg_scale": 7,
            "override_settings": override_settings,
        }
        if hr_scale > 1:
            payload.update(hr_script)

        response = requests.post(url=f'{url}/sdapi/v1/img2img', json=payload).json()

        if 'parameters' in response:
            print(response['parameters'])
        else:
            print(response)

        print(response['info'])

        self.last_gen_info = json.loads(response['info'])

        return self.image_processor.handle_images(response, params['prompt'])


if __name__ == '__main__':
    test_prompt = "1girl, Hatsune Miku, charm, lift up the breast,silk stockings, wetted clothes,coquettish"
    sd_api = SdApi()
    print(sd_api.get_image(test_prompt))
