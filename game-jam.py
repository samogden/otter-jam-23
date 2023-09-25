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

class OpenAIInterface(object):
  cost_tracker = CostTracker()
  @staticmethod
  def get_api_key():
    config = configparser.ConfigParser()
    config_file = os.path.expanduser("~/.config/openai")
    if not os.path.exists(config_file):
      open_api_key = input("Please enter OpenAI API Key: ")
      config["DEFAULT"] = {"OPENAI_API_KEY" : open_api_key}
      with open(config_file, 'w') as fid:
        config.write(fid)
      openai.api_key = open_api_key
    else:
      config.read(config_file)
      openai.api_key = config["DEFAULT"]["OPENAI_API_KEY"]
      
  @classmethod
  def send_msg(cls, messages, model="gpt-3.5-turbo", temperature=0.6):
    response = openai.ChatCompletion.create(
      model=model,
      messages= messages,
      temperature=temperature
    )
    cls.cost_tracker.report_run(response["usage"], model)
    return response.choices[0].message
  
  @classmethod
  def get_image_prompt(cls, str):
    prompt = cls.send_msg([{
      "role" : "user",
      "content" : f"{str}"
    }])
    return prompt["content"]
  
  @classmethod
  def get_image(self, prompt, model="dall-e", size="256x256"):
    response = openai.Image.create(
      prompt=f"{prompt}",
      n=1,
      size=size,
      response_format="b64_json"
    )
    self.cost_tracker.report_run({}, model, size)
    image_buffer = io.BytesIO(
      base64.decodebytes(
        response['data'][0]['b64_json'].encode()
      )
    )
    return image_buffer
  
  @classmethod
  def image_variation(cls, last_image: BytesIO, model="dall-e", size="256x256"):
    last_image.seek(0)
    response = openai.Image.create_variation(
      image=last_image,
      n=1,
      size="512x512",
      response_format="b64_json"
    )
    cls.cost_tracker.report_run({}, model, size)
    image_buffer = io.BytesIO(
      base64.decodebytes(
        response['data'][0]['b64_json'].encode()
      )
    )
    return image_buffer


class Conversation(object):
  def __init__(self, conversation_background=None):
    self.messages = []
    if conversation_background is not None:
      self.add_msg("system", conversation_background)
    self.summary = None
  
  def add_msg(self, kind, msg):
    self.messages.append({
      "role" : kind,
      "content" : msg
    })
  
  def send_msg(self, msg, model="gpt-3.5-turbo"):
    self.add_msg("user", f"{msg}")
    response = OpenAIInterface.send_msg(self.messages)
    self.add_msg("assistant", response["content"])
    return response["content"]
  
  def summarize(self, num_words=200):
    return self.send_msg(f"Please summarize our previous conversation in {num_words} words or less.")
  
  def conversation_loop(self):
    while True:
      msg = input("> ")
      if msg.strip().lower() == "exit":
        self.summary = self.summarize()
        print(f"Summary: {self.summary}")
        break
      elif msg.strip().lower() == "show me":
        last_message = self.messages[-1]["content"]
        prompt = OpenAIInterface.get_image_prompt(f"Make me a 100 word description of an image based on: {last_message}")
        image_buffer = OpenAIInterface.get_image(f"{prompt[:1000]}")
        img = Image.open(image_buffer)
        img.show()
      else:
        resp = self.send_msg(msg)
        print(resp)
      logging.info(f"Total cost: ${OpenAIInterface.cost_tracker.cumulative_cost : 0.6f}")


def run_adventure(adventure_hook):
  
  # Generate some background
  background = Conversation(adventure_hook)
  description = background.send_msg("In 100 words or less, describe the appearance of the bartender.")
  image_buffer = OpenAIInterface.get_image(description)
  img = Image.open(image_buffer)
  img.show()
  description = background.send_msg("In 100 words or less, describe the appearance of the bartender and the bar.")
  
  
  
  conversation_hook = background.send_msg(f"{adventure_hook}.  The bar can be described as: {description}")
  print(conversation_hook)
  conversation = Conversation(conversation_hook)
  conversation.conversation_loop()
  
  continue_answer = input("Would you like to continue your adventure? (y/n) ")
  if continue_answer.lower()[0] == "y":
    summary = conversation.summary
    conversation_hook = background.send_msg(f"In 100 words, describe the scene for the next interaction.  A summary of the previous interaction is: {summary}")
    print(conversation_hook)
    conversation = Conversation(conversation_hook)
    conversation.conversation_loop()
  
  

def main():
  OpenAIInterface.get_api_key()
  
  adventure_hook = "I am entering a fantasy tavern to talk to the bartender about getting a cup of ale and possibly some quests.  The bartender, played by the asisstant, has a gruff personality but is willing to take my money."
  
  run_adventure(adventure_hook)
  
  return
  
  #conv = Conversation("I am entering a fantasy tavern to talk to the bartender about getting a cup of ale and possibly some quests.  The bartender, played by the assistant, has a gruff personality but is willing to take my money.")
  conv = Conversation("The previous interaction is summarized as follows.  You, the assistant, are playing the bartender Gruff.  In the fantasy tavern, the weary traveler approaches the gruff bartender, requesting a flagon of grog and inquiring about any local news. The bartender mentions rumors of bandits causing trouble in the nearby forests and a reward being offered to those who can put an end to their mischief. Another quest involves retrieving a rare magical artifact from a cursed tomb, with a wizard named Zephyrus providing more information. Intrigued, the traveler asks about the rewards for completing the quest. The bartender explains that Zephyrus promises a substantial sum of gold, the potential to enhance one's abilities with the artifact, and the opportunity to gain a reputation as a skilled adventurer. Satisfied with the potential rewards, the traveler expresses interest in pursuing the quest and asks for the bartender's name for future reference. The bartender introduces himself as Gruff, assuring the traveler that he'll likely find him at the tavern upon their return. With gratitude and determination, the traveler sets off to locate the wizard and embark on the perilous quest.")
  while True:
    msg = input("> ")
    if msg.strip().lower() == "exit":
      conv.summarize()
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
  print(f"Summary:\n{conv.summary}")

if __name__ == "__main__":
  main()
