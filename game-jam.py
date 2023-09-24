#!env python
import base64
import configparser
import io
import logging
import os.path
from enum import Enum
from pprint import pprint

import openai
from PIL import Image
from io import BytesIO

import helper
from helper import CostTracker

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

class Conversation(object):
  
  class Msg_Kind(Enum):
    system = "system",
    assistant = "assistant",
    user = "user"
    
  def __init__(self, system_msg=None):
    self.messages = []
    self.cost_tracker = CostTracker()
    if system_msg is not None:
      self.add_msg(system_msg)
    self.last_image = None
  
  def add_msg(self, kind : Msg_Kind, msg):
    self.messages.append({
      "role" : kind,
      "content" : msg
    })
  
  def send_msg(self, msg, model="gpt-3.5-turbo"):
    response = openai.ChatCompletion.create(
      model=model,
      messages= self.messages + [
        {"role" : "user", "content" : f"{msg}"}
      ],
      temperature=0.6
    )
    self.cost_tracker.report_run(response["usage"], model)
    logging.debug(pprint(response))
    
    resp_msg = response.choices[0].message
    return resp_msg["content"]
  
  def get_image(self, prompt, model="dall-e", size="256x256"):
    response = openai.Image.create(
      prompt=f"{prompt}",
      n=1,
      size="512x512",
      response_format="b64_json"
    )
    self.cost_tracker.report_run({}, model, size)
    image_buffer = self.convert_resp_to_image_buffer(response)
    self.last_image = image_buffer
    img = Image.open(image_buffer)
    img.show()
    
  def image_variation(self, prompt, model="dall-e", size="256x256"):
    self.last_image.seek(0)
    response = openai.Image.create_variation(
      image=self.last_image,
      n=1,
      size="512x512",
      response_format="b64_json"
    )
    self.cost_tracker.report_run({}, model, size)
    image_buffer = self.convert_resp_to_image_buffer(response)
    self.last_image = image_buffer
    img = Image.open(image_buffer)
    img.show()
  
  @staticmethod
  def convert_resp_to_image_buffer(response):
    image_buffer = io.BytesIO(
      base64.decodebytes(
        response['data'][0]['b64_json'].encode()
      )
    )
    return image_buffer
      

def main():
  helper.read_api_key()
  
  conv = Conversation()
  while True:
    msg = input("> ")
    if msg.strip().lower() == "exit":
      break
    elif msg.strip().lower() == "new":
      conv = Conversation
      continue
    elif msg.startswith("image:"):
      prompt = ':'.join(msg.split(':')[1:])
      conv.get_image(prompt)
    elif msg.startswith("image variation"):
      prompt = ':'.join(msg.split(':')[1:])
      conv.image_variation(prompt)
    else:
      resp = conv.send_msg(msg)
      print(resp)
    logging.info(f"Total cost: ${conv.cost_tracker.cumulative_cost : 0.6f}")
    print("")

if __name__ == "__main__":
  main()
