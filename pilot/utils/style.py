from termcolor import colored


def red(text):
    return colored(text, 'red')


def red_bold(text):
    return colored(text, 'red', attrs=['bold'])


def yellow(text):
    return colored(text, 'yellow')


def yellow_bold(text):
    return colored(text, 'yellow', attrs=['bold'])


def green(text):
    return colored(text, 'green')


def green_bold(text):
    return colored(text, 'green', attrs=['bold'])


def blue(text):
    return colored(text, 'blue')


def blue_bold(text):
    return colored(text, 'blue', attrs=['bold'])


def cyan(text):
    return colored(text, 'light_cyan')


def white(text):
    return colored(text, 'white')


def white_bold(text):
    return colored(text, 'white', attrs=['bold'])
