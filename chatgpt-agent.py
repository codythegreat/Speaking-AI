#!/usr/bin/env python3

import os
import openai
import sys
import subprocess
import re
import json
import datetime
import requests

response = requests.get("https://ipinfo.io/json")

if response.status_code == 200:
    ipinfo = response.json()
    city = ipinfo['city']
    region = ipinfo['region']

TERM_SUPPORTS_COLOR = os.getenv('TERM') is not None and '256' in os.getenv('TERM')

SYSTEM_PROMPT = f"""
You are an assistant on a Linux (Ubuntu) terminal.
      
User Details:
{f"* location: {city}, {region}" if city and region else ''}
* date: {datetime.datetime.now().strftime("%m-%d-%Y")}
* time: {datetime.datetime.now().strftime("%H:%M %p")}
* PWD: {os.getcwd()}

You can execute commands for the user by wrapping them like this: EXECUTE(command).
      
For example, EXECUTE(cd ~) would take the user to their home directory.

More examples:
User:
Please create a new directory called test and fill it with file1.txt thru file99.txt
Assistant:
EXECUTE(mkdir test)
EXECUTE(for i in {{1..99}}; do touch test/file$i.txt; done)
User:
Can you get me the weather?
Assistant:
EXECUTE(curl "https://wttr.in/Flower+Mound")
      
When asked to create a file or program, be sure to use the EXECUTE(command) syntax to create the file or program.
You can use echo to write text line-by-line into a file.
Do not use programs that require user input, such as top, nano, or apt.
"""

task = sys.argv[1]

openai.api_key = os.getenv("OPENAI_API_KEY")

MEMORY_FOLDER_PATH = 'memory'
MEMORY_FILE_PREFIX = 'chatgpt-memory_'
MEMORY_FILE_EXTENSION = '.json'
MEMORY_FILE_CHAR_LIMIT = 10000

def get_latest_chatgpt_memory_file():
    if not os.path.exists(MEMORY_FOLDER_PATH):
        os.makedirs(MEMORY_FOLDER_PATH)
    memory_files = [f for f in os.listdir(MEMORY_FOLDER_PATH) if os.path.isfile(os.path.join(MEMORY_FOLDER_PATH, f)) 
                   and f.startswith(MEMORY_FILE_PREFIX) and f.endswith(MEMORY_FILE_EXTENSION)]
    if not memory_files:
        return None
    return max(memory_files)

def load_chatgpt_memory():
    latest_file = get_latest_chatgpt_memory_file()
    if latest_file is not None:
        with open(os.path.join(MEMORY_FOLDER_PATH, latest_file), 'r') as f:
            memory_objects = json.load(f)
    else:
        memory_objects = []
    return memory_objects

def save_chatgpt_memory(memory_objects):
    latest_file = get_latest_chatgpt_memory_file()
    now = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    if latest_file is not None and os.stat(os.path.join(MEMORY_FOLDER_PATH, latest_file)).st_size < MEMORY_FILE_CHAR_LIMIT:
        with open(os.path.join(MEMORY_FOLDER_PATH, latest_file), 'w') as f:
            json.dump(memory_objects, f)
    else:
        new_file_name = MEMORY_FILE_PREFIX + now + MEMORY_FILE_EXTENSION
        with open(os.path.join(MEMORY_FOLDER_PATH, new_file_name), 'w') as f:
            json.dump(memory_objects, f)

def notify_if_chatgpt_memory_exceeds_character_limit(memory_objects):
    total_content_length = sum(len(memory_object["content"]) for memory_object in memory_objects)
    if total_content_length > MEMORY_FILE_CHAR_LIMIT:
        warning_message = f"WARNING: chat memory is getting large (>{MEMORY_FILE_CHAR_LIMIT})"
        print(f"\033[91m{warning_message}\033[0m" if TERM_SUPPORTS_COLOR else warning_message)

LOG_DIR = 'log'
IS_LOGGING = True

def get_openai_chatgpt_completion(messages):
    completion = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=messages
    )
    if IS_LOGGING:
        with open(f'{LOG_DIR}/completions.json', 'a') as log_file:
            log_file.write(json.dumps(completion) + '\n')
    return completion


def loop(task):
    memory_objects = load_chatgpt_memory()
    memory_objects.append({"role": "user", "content": task})

    messages=[
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    messages.extend(memory_objects)

    response = get_openai_chatgpt_completion(messages).choices[0].message.content
    memory_objects.append({"role": "assistant", "content": response})

    notify_if_chatgpt_memory_exceeds_character_limit(memory_objects)

    save_chatgpt_memory(memory_objects)

    print(f'\n\033[38;5;24m{response}\033[0m\n' if TERM_SUPPORTS_COLOR else f'{response}\n')

    match = re.findall(r'EXECUTE\((.*)\)', response)
    for command in match:
        handle_command(command)
    
    continuing = input("Continue using chatgpt-agent? (y/n): ") == 'y'
    if continuing:
        task = input("User: ")
        loop(task)


def change_directory(path):
    # convert ~ to an abolute path
    if path.startswith('~'):
        path = os.path.expanduser(path)

    os.chdir(path)
    print(f'\nOUTPUT:\nPWD: {path}')


def handle_command(command):
    print(command)
    canExecute = input("Execute command? (y/n): ") == 'y'

    if canExecute and command.startswith('cd'):
        # whenever we have other commands separated by &&
        # We need to isolate the path we're cd-ing into
        raw_commands = command.split("&&")
        path = raw_commands[0][3:].strip()

        change_directory(path)
  
        # handle remaining commands separated by &&
        if len(raw_commands) > 1:
            for cmd in raw_commands[1:]:
                handle_command(cmd.strip())

    elif canExecute:
        try:
            output = subprocess.check_output(command, shell=True).decode()
        except subprocess.CalledProcessError as e:
            output = e
        print(f'\nOUTPUT:\n{output}')

    else:
        instructions = input("If you'd like to instruct chatgpt-agent, type now: ")
        if instructions != "":
            task = f'{instructions}'
            loop(task)
        exit()


loop(task)