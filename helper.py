#!env python

import configparser
from typing import Dict

import openai
import os

class CostTracker(object):
  
  models = {
    "gpt-3.5-turbo" : {
      "4k" : {
        "input" : 0.0000015,
        "output" : 0.000002
      },
      "16k" : {
        "input" : 0.00003,
        "output" : 0.000004
      }
    },
    "gpt-4" : {
      "8k" : {
        "input" : 0.00003,
        "output" : 0.00006
      },
      "32k" : {
        "input" : 0.00006,
        "output" : 0.00012
      }
    },
    "dall-e" : {
      "1024x1024" : 0.02,
      "512x512" : 0.018,
      "256x256" : 0.016,
    }
  }
  
  def __init__(self):
    self.cumulative_cost = 0.0
  
  def report_run(self, usage : Dict[str,int], model : str, size=None):
    if "gpt" in model:
      self.cumulative_cost += (
          usage["prompt_tokens"] * self.models[model]["4k"]["input"]
          +
          usage["completion_tokens"] * self.models[model]["4k"]["output"]
      )
    elif "dall-e" in model:
      size = size if size is not None else "1024x1024"
      self.cumulative_cost += self.models[model][size]

def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613"):
  """Returns the number of tokens used by a list of messages."""
  # From https://platform.openai.com/docs/guides/gpt/managing-tokens
  try:
    encoding = tiktoken.encoding_for_model(model)
  except KeyError:
    encoding = tiktoken.get_encoding("cl100k_base")
  if model == "gpt-3.5-turbo-0613":  # note: future models may deviate from this
    num_tokens = 0
    for message in messages:
      num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
      for key, value in message.items():
        num_tokens += len(encoding.encode(value))
        if key == "name":  # if there's a name, the role is omitted
          num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens
  else:
    raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}.
  See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")