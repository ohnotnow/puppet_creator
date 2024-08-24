import re
import os

def remove_markdown(text):
    text = re.sub(r"```.*\n", "", text)
    text = re.sub(r"```", "", text)
    return text

def sanitize_filename(filename):
    # make sure the llm filename isn't mad
    filename = filename.replace(" ", "_")
    filename = filename.replace("/", "_")
    filename = filename.replace("\\", "_")
    filename = filename.replace(":", "_")
    filename = filename.replace("*", "_")
    filename = filename.replace("?", "_")
    filename = filename.replace("\"", "_")
    filename = filename.replace("<", "_")
    filename = filename.replace(">", "_")
    filename = filename.replace("|", "_")
    # use a regex to remove and extraneous markdown backticks (possibly with language indicators)
    filename = re.sub(r"```.*\n", "", filename)
    if filename.startswith("."):
        filename = filename[1:]
    if not filename.endswith(".pp"):
        filename = filename + ".pp"
    if not filename:
        filename = "default_module.pp"
    return filename


def save_file(contents, filename):
    with open(filename, "w") as f:
        f.write(contents)

def create_output_directory(name="outputs"):
    if not os.path.exists(name):
        os.makedirs(name, exist_ok=True)

def get_requirements(requirements_file):
    if requirements_file:
        with open(requirements_file, "r") as f:
            requirements = f.read()
    else:
        requirements = input("Enter your requirements:\n")
    return requirements
