
# Start with Debian
FROM debian:bookworm
# Install necessary packages and Puppet
RUN apt-get update && apt-get upgrade && apt-get install curl -y
RUN curl -OL https://apt.puppet.com/puppet7-release-bookworm.deb
RUN dpkg -i puppet7-release-bookworm.deb
RUN apt-get install -y python3 python3-pip python3-pytest python3-testinfra puppet-agent
RUN apt-get clean

# Set up Puppet
RUN /usr/bin/puppet config set server puppet.eng.gla.ac.uk --section main

# Ensure Puppet bin directory is in PATH
# ENV PATH="/opt/puppetlabs/bin:$PATH"

# Command to keep the container running
CMD ["tail", "-f", "/dev/null"]
