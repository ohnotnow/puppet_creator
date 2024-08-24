# Project: Puppet Module Generator

## Description
The Puppet Module Generator is a command-line tool designed to help users create Puppet modules based on given requirements. It leverages a language model to think through the requirements, generate the module, and suggest a filename, ensuring that the module adheres to best practices and is compatible with Rocky Linux, Debian, and Ubuntu.

## Features
- Analyzes and processes user-provided requirements.
- Generates Puppet modules with inline comments.
- Lints and tests the generated module.
- Suggests and sanitizes filenames for the module.
- Tracks the total cost and time taken for the module generation process.

## Installation

### Requirements
- Python 3.6+
- `pip` (Python package installer)
- A supported LLM model

### Installation Steps

1. **Clone the repository**
    ```sh
    git clone https://github.com/ohnotnow/puppet_creator
    cd puppet_creator
    ```

2. **Set up a virtual environment and install dependencies**

    #### On MacOS and Ubuntu:
    ```sh
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

    #### On Windows:
    ```sh
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    ```

## Usage

Run the script using the command line. You can provide a file containing your requirements or enter them manually.

### Command-Line Arguments

- `--requirements-file`: Path to a text file containing the module requirements.
- `--model`: The LLM model to use (default: `gpt-4o-2024-08-06`).
- `--vendor`: The LLM vendor to use (not needed for openai/anthropic models).
- `--rebuild`: Force a rebuild of the Docker containers used to test the module

### Example Usage

#### Using a requirements file:
```sh
python main.py --requirements-file path/to/module_requirements.txt
```

#### Entering requirements manually:
```sh
python main.py
```

#### Using different models:
You can use different models and API providers if you like.  You will need to set the appropriate environment variables to access them, for instance :
```sh
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export ANYSCALE_API_KEY=...
export GROQ_API_KEY=....
```
And then:
```sh
python main.py --model=claude-3-5-sonnet-20240620
python main.py --model=llama3-70b-8192 --vendor=groq
```

## Detailed Steps

1. **Read Requirements**: Reads the requirements either from a file or manual input.
2. **Think Through Requirements**: Uses the language model to analyze and provide thoughts on the requirements.
3. **Create Module**: Generates a Puppet module based on the requirements and the model's thoughts.
4. **Lint Module**: Ensures the generated module adheres to best practices.
5. **Test Module**: Runs tests on the generated module to ensure functionality.
6. **Create Filename**: Suggests a Linux filesystem-safe filename for the module.
7. **Save Module**: Saves the module with the generated filename.

## Example

```sh
$ python main.py
Enter your requirements:
install apache and mod_php. use the remi repo for yum and the andrej one for apt. assume php 8.3.  make sure apache and php are kept up to date.
⠦ Starting Rocky Docker container...Image puppet-rocky-8:latest found
⠹ Starting Debian Docker container...Image puppet-debian-bookworm:latest found
Module saved to outputs/apache_php83_remi_andrej.pp


Total time: 62.54 seconds
Total cost: $0.0487

$ cat outputs/apache_php83_remi_andrej.pp
```
```ruby
class apache_php {
  # Define parameters with default values
  $php_version = '8.3'
  $apache_package = $facts['os']['family'] ? {
    'RedHat' => 'httpd',
    'Debian' => 'apache2',
    default  => 'apache2',
  }
  $php_package = $facts['os']['family'] ? {
    'RedHat' => "php${php_version.replace('.', '')}",
    'Debian' => "php${php_version}",
    default  => "php${php_version}",
  }
  $mod_php_package = $facts['os']['family'] ? {
    'RedHat' => "php${php_version.replace('.', '')}-php",
    'Debian' => "libapache2-mod-php${php_version}",
    default  => "libapache2-mod-php${php_version}",
  }

  # Manage repositories based on OS family
  if $facts['os']['family'] == 'RedHat' {
    # Ensure EPEL is enabled
    package { 'epel-release':
      ensure => installed,
    }

    # Add Remi repository for PHP
    yumrepo { 'remi':
      baseurl  => "http://rpms.remirepo.net/enterprise/\$releasever/remi/\$basearch/",
      gpgkey   => 'https://rpms.remirepo.net/RPM-GPG-KEY-remi',
      enabled  => 1,
      gpgcheck => 1,
    }
  } elsif $facts['os']['family'] == 'Debian' {
    # Ensure apt-transport-https is installed
    package { 'apt-transport-https':
    'Debian' => "libapache2-mod-php${php_version}",
    default  => "libapache2-mod-php${php_version}",
  }

  # Manage repositories based on OS family
  if $facts['os']['family'] == 'RedHat' {
    # Ensure EPEL is enabled
    package { 'epel-release':
      ensure => installed,
    }

    # Add Remi repository for PHP
    yumrepo { 'remi':
      baseurl  => "http://rpms.remirepo.net/enterprise/\$releasever/remi/\$basearch/",
      gpgkey   => 'https://rpms.remirepo.net/RPM-GPG-KEY-remi',
      enabled  => 1,
      gpgcheck => 1,
    }
  } elsif $facts['os']['family'] == 'Debian' {
    # Ensure apt-transport-https is installed
    package { 'apt-transport-https':
      ensure => installed,
    }

    # Add Ondřej Surý PPA for PHP
    apt::source { 'ondrej-php':
      location => 'ppa:ondrej/php',
      release  => $facts['lsbdistcodename'],
      repos    => 'main',
    }

    # Update apt cache
    exec { 'apt_update':
      command     => '/usr/bin/apt-get update',
      refreshonly => true,
      subscribe   => Apt::Source['ondrej-php'],
    }
  }

  # Install Apache and PHP packages
  package { [$apache_package, $php_package, $mod_php_package]:
    ensure => latest,
  }

  # Ensure Apache service is running and enabled
  service { 'apache':
    name    => $apache_package,
    ensure  => running,
    enable  => true,
    require => Package[$apache_package],
  }
}
```

## License
MIT License
