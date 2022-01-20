# nj-mvc-watch

Poller to announce new appointment availabilities with the [New Jersey Motor Vehicle Commission](https://telegov.njportal.com/njmvc/AppointmentWizard/)

## Requirements

This tool requires `python3.9` or above, and the requirements in requirements.txt:

`pip install -r requirements.txt`

## Telegram Bot

To create a Telegram bot, follow [telegram's guide](https://core.telegram.org/bots#6-botfather).

Save the bot token and the chat/group id to which the bot will need to send the announces, you will need to input it in your configuration file


## Configuration

Copy the [`config.sample.yaml`](config.sample.yaml) file to `config.yaml` (or another filename of your chosing).

Update the file with your custom values.

## Running

To execute the bot, just run:

`python3 mvcnj.py [configfile.yaml]`

You can omit the config file name if you used the default `config.yaml` location.
