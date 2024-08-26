import prompts

def get_llm_thoughts(requirements, bot):
    messages = [
        {
            "role": "system",
            "content": prompts.initial_thoughts_prompt
        },
        {
            "role": "user",
            "content": f"Hi! I would like your thoughts on what to consider when writing a Puppet module to satisfy the following requirements:\n\n{requirements}"
        }
    ]
    response = bot.chat(messages, temperature=0.1)
    return response

def create_module(requirements, llm_thoughts, bot):
    messages = [
        {
            "role": "system",
            "content": prompts.write_module_prompt
        },
        {
            "role": "user",
            "content": f"Hi! I would like you to create a puppet module for the following requirements:\n\n{requirements}\n\nPlease take into account the following thoughts:\n\n{llm_thoughts}"
        }
    ]
    response = bot.chat(messages, temperature=0.1)
    return response

def document_module(module, bot):
    messages = [
        {
            "role": "system",
            "content": prompts.document_module_prompt
        },
        {
            "role": "user",
            "content": f"Hi! I would like you to add puppet strings to the following puppet module:\n\n{module}"
        }
    ]
    response = bot.chat(messages, temperature=0.1)
    return response

def create_test(requirements, module, llm_thoughts, bot):
    messages = [
        {
            "role": "system",
            "content": prompts.test_module_prompt
        },
        {
            "role": "user",
            "content": f"Hi! I would like you to create a python TestInfra script to test the results of the following puppet module:\n\n{module}\n\nPlease take into account the following original requirements and thoughts:\n\n{requirements}\n\n{llm_thoughts}"
        }
    ]
    response = bot.chat(messages, temperature=0.1)
    return response

def create_filename(requirements, bot):
    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant who is an expert with the Puppet system configuration system.  The user will provide you with the requirements they have for a new module, but they have difficulty thinking of a good filename which is Linux filesystem safe.  You should read the requirements and think of a concise filename.  Please resond with only the filename so that the user can copy and paste it easily."
        },
        {
            "role": "user",
            "content": f"Hi! I have the following requirements for a puppet module - but I can't think of a good filename!  Requirements:\n\n{requirements}"
        }
    ]
    response = bot.chat(messages, temperature=0.1)

    return response
