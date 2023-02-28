#!/usr/bin/env python3

import os
import openai
import sys
import subprocess

openai.api_key = os.getenv("OPENAI_API_KEY")

prompt="""You're an autonomous AI on an Ubuntu linux terminal.\n\nYou'll take an instruction such as \"create 50 files, called `file_01.txt` to `file_50.txt`\", and you'll create commands that accomplish these tasks. Please only give one command at a time. I'll reply each time with the output from your command. If a command didn't go as you'd expected, feel free to modify and run it again. When you feel you've completed the task reply DONE. \n\nTASK:\ncreate a new dir called \"python3-app\", cd into it and create a README.md file that says \"### Hello World!\"\n\nCOMMAND:\nmkdir python3-app\nOUTPUT:\n\nCOMMAND:\ncd python3-app\nOUTPUT:\n\nCOMMAND:\necho \"### Hello World!\" > README.md\nOUTPUT:\n\nCOMMAND:\nDONE\n\nTASK:\n"""
 
prompt += sys.argv[1]
prompt += '\n\nCOMMAND:\n'

def loop(prompt):
    response = openai.Completion.create(
      model="text-davinci-003",
      prompt=prompt,
      temperature=0,
      max_tokens=256,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0,
      stop=["OUTPUT:", "\n"]
    )

    command = response.choices[0].text

    if command == 'DONE':
        exit()

    print(command)
    canExecute = input("Execute command? (y/n)") == 'y'

    if canExecute:
        prompt += command

        try:
            output = subprocess.check_output(command, shell=True).decode()
        except subprocess.CalledProcessError as e:
            output = e

        output_max_length = 512
        if len(output) > output_max_length:
            exit()

        print(f'\nOUTPUT:\n{output}')
        prompt += f'\nOUTPUT:\n{output}'
        prompt += '\nCOMMAND:\n'
        loop(prompt)
    else:
        instructions = input("If you'd like to instruct gpt-agent, type now:")
        if instructions == "":
            exit()
        else:
            prompt += f'\nOUTPUT:\n{instructions}'
            prompt += '\nCOMMAND:\n'
            loop(prompt)

loop(prompt)
