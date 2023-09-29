from colorama import Fore, Style

def red(text):
    return f'{Fore.RED}{text}{Style.RESET_ALL}'


def red_bold(text):
    return f'{Fore.RED}{Style.BRIGHT}{text}{Style.RESET_ALL}'


def yellow(text):
    return f'{Fore.YELLOW}{text}{Style.RESET_ALL}'


def yellow_bold(text):
    return f'{Fore.YELLOW}{Style.BRIGHT}{text}{Style.RESET_ALL}'


def green(text):
    return f'{Fore.GREEN}{text}{Style.RESET_ALL}'


def green_bold(text):
    return f'{Fore.GREEN}{Style.BRIGHT}{text}{Style.RESET_ALL}'


def blue(text):
    return f'{Fore.BLUE}{text}{Style.RESET_ALL}'


def blue_bold(text):
    return f'{Fore.BLUE}{Style.BRIGHT}{text}{Style.RESET_ALL}'


def cyan(text):
    return f'{Fore.CYAN}{text}{Style.RESET_ALL}'


def white(text):
    return f'{Fore.WHITE}{text}{Style.RESET_ALL}'


def white_bold(text):
    return f'{Fore.WHITE}{Style.BRIGHT}{text}{Style.RESET_ALL}'
