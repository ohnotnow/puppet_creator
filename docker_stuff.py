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
