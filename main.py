import datetime
import argparse
import os
from yaspin import yaspin

from gepetto import bot_factory, gpt
from helpers import remove_markdown, sanitize_filename, save_file, create_output_directory, get_requirements
from llm_steps import get_llm_thoughts, create_module, document_module, create_test, create_filename
from docker_stuff import start_rocky_container, start_debian_container, tidy_up
from steps import lint_module, test_module_runs, test_module_works

def main(model=gpt.Model.GPT_4_OMNI_0806.value[0], vendor="", requirements_file="", rebuild=False):
    create_output_directory()

    requirements = get_requirements(requirements_file)
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

    lint_in_container(module_text)

    total_cost = test_in_container("Rocky", 8, requirements, module_text, llm_thoughts, bot, total_cost, rebuild)
    total_cost = test_in_container("Debian", "bookworm", requirements, module_text, llm_thoughts, bot, total_cost, rebuild)

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
    print("\n\n")
    print(f"Module saved to {safe_filename}")
    print(f"Total time: {round(elapsed_time, 2)} seconds")
    print(f"Total cost: ${round(total_cost, 5)}")

def lint_in_container(module_text):
    with yaspin(text="Starting Linting Docker container...", color="green") as spinner:
        container = start_rocky_container(version=8, minimal=False, rebuild=False)
    with yaspin(text="Linting module...", color="yellow") as spinner:
        exit_code, lint_output = lint_module(module_text, container)
        if exit_code != 0:
            print("Module failed linting. Exiting.")
            print(module_text)
            print(lint_output)
            tidy_up(container)
            exit(1)
    with yaspin(text="Removing lint container...", color="red") as spinner:
        tidy_up(container)
    return True

def test_in_container(container_type, version, requirements, module_text, llm_thoughts, bot, total_cost, rebuild):
    with yaspin(text=f"Starting {container_type} Docker container...", color="green") as spinner:
        if container_type == "Rocky":
            container = start_rocky_container(version=version, minimal=False, rebuild=rebuild)
        else:
            container = start_debian_container(version=version, minimal=False, rebuild=rebuild)

    try:
        with yaspin(text=f"Testing module runs in {container_type}...", color="green") as spinner:
            exit_code, output = test_module_runs(module_text, container)
            if exit_code != 0:
                raise RuntimeError(f"Module failed to run with exit code {exit_code}\nOutput: {output}\nModule:\n{module_text}")

        with yaspin(text=f"Testing module works in {container_type}...", color="green") as spinner:
            testinfra = create_test(requirements, module_text, llm_thoughts.message, bot)
            test_text = remove_markdown(testinfra.message)
            total_cost += testinfra.cost
            exit_code, output = test_module_works(module_text, test_text, container)
            if exit_code != 0:
                raise RuntimeError(f"Module failed its tests with exit code {exit_code}\nOutput: {output}\nModule:\n{module_text}\nTestInfra script:\n{test_text}")

    finally:
        tidy_up(container)

    return total_cost

if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("--requirements-file", type=str, default="", help="A text file containing your requirements")
    argp.add_argument("--model", type=str, default=gpt.Model.GPT_4_OMNI_0806.value[0], help="The LLM model to use")
    argp.add_argument("--vendor", type=str, default="openai", help="The LLM vendor to use (not needed for openai/anthropic models)")
    argp.add_argument("--rebuild", action="store_true", help="Rebuild the Docker containers fresh")
    args = argp.parse_args()
    main(model=args.model, vendor=args.vendor, requirements_file=args.requirements_file, rebuild=args.rebuild)
