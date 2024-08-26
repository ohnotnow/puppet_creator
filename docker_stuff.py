import docker
import io
import os
import tarfile
from yaspin import yaspin

def get_dockerfile(distro_name, version, minimal=False):
    if distro_name == 'rocky':
        return get_rocky_dockerfile(version, minimal)
    if distro_name == 'debian':
        return get_debian_dockerfile(version, minimal)
    if distro_name == 'ubuntu':
        return get_ubuntu_dockerfile(version, minimal)

def get_rocky_dockerfile(version, minimal=False):
    return f"""
# Start with RockyLinux
FROM rockylinux:{version}{'-minimal' if minimal else ''}

# Install necessary packages and Puppet
RUN rpm -Uvh https://yum.puppet.com/puppet7-release-el-{version}.noarch.rpm
RUN (dnf update -y || yum update -y)
RUN (dnf install -y python3 python3-pip || yum install -y python3 python3-pip)
RUN (dnf install -y puppet-agent || yum install -y puppet-agent)
RUN (dnf clean all || yum clean all)

# Install TestInfra and its dependencies
RUN pip3 install pytest pytest-testinfra

# Set up Puppet
RUN /opt/puppetlabs/bin/puppet config set server puppet.eng.gla.ac.uk --section main

# Ensure Puppet bin directory is in PATH
ENV PATH="/opt/puppetlabs/bin:$PATH"

# Command to keep the container running
CMD ["tail", "-f", "/dev/null"]
"""

def get_debian_dockerfile(version, minimal=False):
    return f"""
# Start with Debian
FROM debian:{version}{'-slim' if minimal else ''}
# Install necessary packages and Puppet
RUN apt-get update && apt-get upgrade && apt-get install curl -y
RUN curl -OL https://apt.puppet.com/puppet7-release-bookworm.deb
RUN dpkg -i puppet7-release-{version}.deb
RUN apt-get install -y python3 python3-pip python3-pytest python3-testinfra puppet-agent
RUN apt-get clean

# Set up Puppet
RUN /usr/bin/puppet config set server puppet.eng.gla.ac.uk --section main

# Ensure Puppet bin directory is in PATH
# ENV PATH="/opt/puppetlabs/bin:$PATH"

# Command to keep the container running
CMD ["tail", "-f", "/dev/null"]
"""

def get_ubuntu_dockerfile(version, minimal=False):
    return f"""
# Start with Ubuntu
FROM ubuntu:{version}{'-minimal' if minimal else ''}
# Install necessary packages and Puppet
RUN wget https://apt.puppet.com/puppet7-release-{version}.deb
RUN dpkg -i puppet7-release-{version}.deb
RUN apt-get update
RUN apt-get install -y python3 python3-pip puppet-agent
RUN apt-get clean

# Install TestInfra and its dependencies
RUN pip3 install pytest pytest-testinfra

# Set up Puppet
RUN /opt/puppetlabs/bin/puppet config set server puppet.eng.gla.ac.uk --section main

# Ensure Puppet bin directory is in PATH
ENV PATH="/opt/puppetlabs/bin:$PATH"

# Command to keep the container running
CMD ["tail", "-f", "/dev/null"]
"""

def copy_to_container(container, src, dst):
    # we need to create a tarball of the source file to copy it in - dockerism
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode='w') as tar:
        tar.add(src, arcname=os.path.basename(src))
    tar_stream.seek(0)

    # copy/untar the file into the container
    container.put_archive(os.path.dirname(dst), tar_stream)

def get_docker_client():
    return docker.from_env()

def build_rocky_container(version=8, minimal=False, rebuild=False):
    image_tag = f"puppet-rocky-{version}:latest"
    dockerfile = get_dockerfile('rocky', version, minimal)
    build_container(image_tag, dockerfile, rebuild)
    return image_tag

def build_debian_container(version=12, minimal=False, rebuild=False):
    image_tag = f"puppet-debian-{version}:latest"
    dockerfile = get_dockerfile('debian', version, minimal)
    build_container(image_tag, dockerfile, rebuild)
    return image_tag

def start_rocky_container(version=8, minimal=False, rebuild=False):
    container_name = f"puppet-rocky-{version}-test-container"
    image_tag = build_rocky_container(version=version, minimal=minimal, rebuild=rebuild)
    container = start_container(image_tag, container_name)
    return container

def start_debian_container(version=12, minimal=False, rebuild=False):
    container_name = f"puppet-debian-{version}-test-container"
    image_tag = build_debian_container(version=version, minimal=minimal, rebuild=rebuild)
    container = start_container(image_tag, container_name)
    return container

def start_container(image_tag, name):
    client = get_docker_client()
    remove_existing_container(name)
    try:
        container = client.containers.run(
            image_tag,
            detach=True,
            name=name,
        )
        return container
    except docker.errors.DockerException as e:
        print(f"Error creating container: {e}")
        exit(1)
    except Exception as e:
        print(f"Error creating container: {e}")
        exit(1)

def remove_existing_container(container_name: str) -> bool:
    client = get_docker_client()
    try:
        container = client.containers.get(container_name)
        tidy_up(container)
    except docker.errors.DockerException as e:
        pass

def build_container(image_tag, dockerfile, rebuild=False):
    client = get_docker_client()
    if not rebuild:
        try:
            client.images.get(image_tag)
            print(f"Using cached image {image_tag}")
            return image_tag
        except docker.errors.ImageNotFound:
            print(f"Image {image_tag} not found. Building...")

    with open('Dockerfile', 'w') as f:
        f.write(dockerfile)

    try:
        client.images.build(
            path="./",
            tag=image_tag,
            rm=True,
            nocache=rebuild
        )
    except docker.errors.BuildError as e:
        print(e)
        exit(1)

    return image_tag

def exec_in_container(container, command):
    exec_result = container.exec_run(command)
    return exec_result.exit_code, exec_result.output.decode('utf-8')

def tidy_up(container):
    container.stop()
    container.remove()
