import datetime
import argparse
import re
import subprocess
import os
import io
import tarfile
import concurrent.futures
from yaspin import yaspin
import docker
from gepetto import bot_factory, gpt
import prompts
import docker_stuff

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
            "content": f"Hi! I would like you to thoroughly document the following puppet module with puppet strings:\n\n{module}"
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


def lint_module(module, container):
    with open("temp_module.pp", "w") as f:
        f.write(module)

    copy_to_container(container, "temp_module.pp", "/tmp/")

    exit_code, output = exec_in_container(container, "puppet parser validate /tmp/temp_module.pp")
    return exit_code, output

def copy_to_container(container, src, dst):
    # Create a tarfile object
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode='w') as tar:
        tar.add(src, arcname=os.path.basename(src))
    tar_stream.seek(0)

    # Copy the file to the container
    container.put_archive(os.path.dirname(dst), tar_stream)


def get_docker_client():
    return docker.from_env()

def build_rocky_container(version=8, minimal=False):
    dockerfile = docker_stuff.get_dockerfile('rocky', version, minimal)
    with open('Dockerfile', 'w') as f:
        f.write(dockerfile)

    client = get_docker_client()
    image_tag = f"puppet-rocky-{version}:latest"

    try:
        client.images.build(
            path="./",
            tag=image_tag,
            rm=True,
            nocache=False
        )
    except docker.errors.BuildError as e:
        print(e)
        exit(1)

    try:
            client.images.get(image_tag)
            print(f"Image {image_tag} found")
    except docker.errors.ImageNotFound:
            print(f"Image {image_tag} not found. Please build the image first.")
            exit(1)

    return image_tag

def start_rocky_container(version=8, minimal=False):
    image_tag = build_rocky_container(version=version, minimal=minimal)
    client = get_docker_client()

    try:
        container = client.containers.run(
            image_tag,
            detach=True,
            name=f"puppet-rocky-{version}-test-container",
        )
        return container
    except docker.errors.DockerException as e:
        print(f"Error creating container: {e}")
        exit(1)
    except Exception as e:
        print(f"Error creating container: {e}")
        exit(1)

def build_debian_container(version=12, minimal=False):
    dockerfile = docker_stuff.get_dockerfile('debian', version, minimal)
    with open('Dockerfile', 'w') as f:
        f.write(dockerfile)

    client = get_docker_client()
    image_tag = f"puppet-debian-{version}:latest"

    try:
        client.images.build(
            path="./",
            tag=image_tag,
            rm=True,
            nocache=False
        )
    except docker.errors.BuildError as e:
        print(e)
        exit(1)

    try:
            client.images.get(image_tag)
            print(f"Image {image_tag} found")
    except docker.errors.ImageNotFound:
            print(f"Image {image_tag} not found. Please build the image first.")
            exit(1)

    return image_tag

def start_debian_container(version=12, minimal=False):
    image_tag = build_debian_container(version=version, minimal=minimal)
    client = get_docker_client()

    try:
        container = client.containers.run(
            image_tag,
            detach=True,
            name=f"puppet-debian-{version}-test-container",
        )
        return container
    except docker.errors.DockerException as e:
        print(f"Error creating container: {e}")
        exit(1)
    except Exception as e:
        print(f"Error creating container: {e}")
        exit(1)

def exec_in_container(container, command):
    exec_result = container.exec_run(command)
    return exec_result.exit_code, exec_result.output.decode('utf-8')

def test_module_runs(module, container):
    with open("temp_module.pp", "w") as f:
        f.write(module)
    copy_to_container(container, "temp_module.pp", "/tmp/")
    exit_code, output = exec_in_container(container, "puppet apply /tmp/temp_module.pp")
    return exit_code, output

def test_module_works(module, infratest_code, container):
    with open("temp_module.pp", "w") as f:
        f.write(module)
    copy_to_container(container, "temp_module.pp", "/tmp/")
    with open("testinfra_script.py", "w") as f:
        f.write(infratest_code)
    copy_to_container(container, "testinfra_script.py", "/tmp/")
    exit_code, output = exec_in_container(container, "puppet apply /tmp/temp_module.pp && python3 /tmp/testinfra_script.py")
    return exit_code, output

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

def save_file(contents, filename):
    with open(filename, "w") as f:
        f.write(contents)

def tidy_up(container):
    with yaspin(text=f"Tidying up container {container.name}...", color="red") as spinner:
        container.stop()
        container.remove()

def main(model=gpt.Model.GPT_4_OMNI_0806.value[0], vendor="", requirements_file=""):
    # if the "outputs" directory doesn't exist, create it
    if not os.path.exists("outputs"):
        os.makedirs("outputs", exist_ok=True)

    if requirements_file:
        with open(requirements_file, "r") as f:
            requirements = f.read()
    else:
        requirements = input("Enter your requirements:\n")
    if not requirements:
        print("No requirements provided. Exiting.")
        exit(1)

    start_time = datetime.datetime.now()
    total_cost = 0
    bot = bot_factory.get_bot(model=model, vendor=vendor)

    with yaspin(text="Thinking through requirements...", color="magenta") as spinner:
        llm_thoughts = get_llm_thoughts(requirements, bot)
        total_cost += llm_thoughts.cost
    with yaspin(text="Creating module...", color="cyan") as spinner:
        module = create_module(requirements, llm_thoughts.message, bot)
        total_cost += module.cost
        module_text = remove_markdown(module.message)
    with yaspin(text="Documenting module...", color="cyan") as spinner:
        documented_module = document_module(module_text, bot)
        total_cost += documented_module.cost
        module_text = remove_markdown(documented_module.message)

    with yaspin(text="Starting Rocky Docker container...", color="green") as spinner:
        container = start_rocky_container(version=8, minimal=False)

    with yaspin(text="Linting module...", color="yellow") as spinner:
        module_is_valid = lint_module(module_text, container)
        if not module_is_valid:
            print("Module failed linting. Exiting.")
            print(module.message)
            exit(1)

    with yaspin(text="Testing module runs in Rocky...", color="green") as spinner:
        exit_code, output = test_module_runs(module_text, container)
        if exit_code != 0:
            print(f"Module failed to run with exit code {exit_code}")
            print(f"Output: {output}")
            print(f"Module:\n{module_text}")
            tidy_up(container)
            exit(1)

    with yaspin(text="Testing module works in Rocky...", color="green") as spinner:
        testinfra = create_test(requirements, module_text, llm_thoughts.message, bot)
        test_text = remove_markdown(testinfra.message)
        total_cost += testinfra.cost
        exit_code, output = test_module_works(module_text, test_text, container)
        if exit_code != 0:
            print(f"Module failed it's tests with exit code {exit_code}")
            print(f"Output: {output}")
            print(f"Module:\n{module}")
            print(f"TestInfra script:\n{test_text}")
            tidy_up(container)
            exit(1)

    tidy_up(container)

    with yaspin(text="Starting Debian Docker container...", color="green") as spinner:
        container = start_debian_container(version="bookworm", minimal=False)

    with yaspin(text="Testing module runs in Debian...", color="green") as spinner:
        exit_code, output = test_module_runs(module_text, container)
        if exit_code != 0:
            print(f"Module failed to run with exit code {exit_code}")
            print(f"Output: {output}")
            print(f"Module:\n{module_text}")
            tidy_up(container)
            exit(1)

    with yaspin(text="Testing module works in Debian...", color="green") as spinner:
        testinfra = create_test(requirements, module_text, llm_thoughts.message, bot)
        test_text = remove_markdown(testinfra.message)
        total_cost += testinfra.cost
        exit_code, output = test_module_works(module_text, test_text, container)
        if exit_code != 0:
            print(f"Module failed it's tests with exit code {exit_code}")
            print(f"Output: {output}")
            print(f"Module:\n{module}")
            print(f"TestInfra script:\n{test_text}")
            tidy_up(container)
            exit(1)

    tidy_up(container)

    with yaspin(text="Creating filename...", color="red") as spinner:
        filename = create_filename(requirements, bot)
        total_cost += filename.cost
    safe_filename = os.path.join("outputs", sanitize_filename(filename.message))
    with yaspin(text=f"Saving module to {safe_filename}...", color="blue") as spinner:
        save_file(module.message, safe_filename)

    # remove temp files
    os.remove("temp_module.pp")
    # os.remove("testinfra_script.py")

    end_time = datetime.datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()
    print(f"Module saved to {safe_filename}")
    print(f"\n\nTotal time: {round(elapsed_time, 2)} seconds")
    print(f"Total cost: ${round(total_cost, 5)}")

if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("--requirements-file", type=str, default="", help="A text file containing your requirements")
    argp.add_argument("--model", type=str, default=gpt.Model.GPT_4_OMNI_0806.value[0], help="The LLM model to use")
    argp.add_argument("--vendor", type=str, default="openai", help="The LLM vendor to use (not needed for openai/anthropic models)")
    args = argp.parse_args()
    main(model=args.model, vendor=args.vendor, requirements_file=args.requirements_file)
