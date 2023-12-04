from IPython.display import Markdown,display
from openai import OpenAI
import requests
import json, io
import base64
from PIL import Image
import numpy as np
import os
import copy

def printmd(string):
    display(Markdown(string))


class gpt4_v_helper():
    def __init__(self, key_file_path='./key/rilab_key.txt', max_tokens = 300, temperature = 0.0, n = 1, stop = [], VERBOSE=True):
        api_key = self.set_openai_api_key_from_txt(key_file_path,VERBOSE=VERBOSE)
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
            }
        self.client = OpenAI(api_key=api_key)
        self.messages = []
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.n = n
        self.stop = stop

    def set_system_prompt(self, system_prompt):
        self.messages.append({"role": "system", "content": system_prompt})
    
    def ask(self, question, image_paths = [], APPEND=True):
        content = [{"type": "text", "text": question}]
        for image_path in image_paths:
            base64_image = self.encode_image(image_path)
            image_message = {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            content.append(image_message)
        user_message = {
            "role": "user",
            "content": content
        }
        self.messages.append(user_message)
        payload = self.create_payload()
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=self.headers, json=payload)
        res = response.json()['choices'][0]['message']['content']
        print(response.json()['choices'][0]['message'])
        if APPEND:
            self.messages.append({"role": "assistant", "content": res})
        return res
    
    def text_to_image(self, text):
        '''
        given text, return image in numpy array
        '''
        response = self.client.images.generate(
            model="dall-e-3",
            prompt=text,
            size="1024x1024",
            quality="standard",
            n=1,response_format="b64_json"
        )
        base_ = response.data[0].b64_json
        decoded = base64.b64decode(base_)
        img = Image.open(io.BytesIO(decoded))
        return np.array(img)
    
    def image_edit_with_text(self, image, mask_boxs, text, path="./", num=1):
        '''
        given image, mask, text, return image in numpy array
        mask_box: [x1,y1,x2,y2]
        '''
        image_path = os.path.join(path, "ori_img.png")
        mask_path = os.path.join(path, "mask.png")


        h_o, w_o, _ = image.shape
        ori_image = Image.fromarray(image)
        ori_img = ori_image.convert('RGBA')
        ori_img.save(image_path)

        mask = copy.deepcopy(ori_img)
        mask = np.array(mask)
        for mask_box in mask_boxs:
            mask[mask_box[1]:mask_box[3],mask_box[0]:mask_box[2],-1] = 0
        mask = Image.fromarray(mask)
        mask.save(mask_path)

        response = self.client.images.edit(
            model="dall-e-2",
            image=open(image_path, "rb"),
            mask=open(mask_path, "rb"),
            prompt=text,
            n=num,
            size="1024x1024",response_format="b64_json"
            )
        res = []
        for i in range(num):
            base_ = response.data[i].b64_json
            decoded = base64.b64decode(base_)
            img = Image.open(io.BytesIO(decoded))
            img = img.resize((w_o, h_o))
            img = np.array(img)
            res.append(img)
        # if num ==1:   
        #     return img
        return res

    def reset(self):
        self.messages = []
        
    def set_openai_api_key_from_txt(self, key_path='./key/rilab_key.txt',VERBOSE=True):
        """
            Set OpenAI API Key from a txt file
        """
        with open(key_path, 'r') as f: 
            OPENAI_API_KEY = f.read()
        if VERBOSE:
            printmd("OPENAI KEY SET")
        return OPENAI_API_KEY
    
    def create_payload(self):
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": self.messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "n": self.n
        }
        if len(self.stop) > 0:
            payload["stop"] = self.stop
        return payload
    
    # Function to encode the image
    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')