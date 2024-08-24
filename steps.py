from docker_stuff import exec_in_container, copy_to_container

def lint_module(module, container):
    with open("temp_module.pp", "w") as f:
        f.write(module)

    copy_to_container(container, "temp_module.pp", "/tmp/")

    exit_code, output = exec_in_container(container, "puppet parser validate /tmp/temp_module.pp")
    return exit_code, output

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
