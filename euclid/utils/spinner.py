from yaspin import yaspin
from yaspin.spinners import Spinners


def spinner_start(text="Processing..."):
    spinner = yaspin(Spinners.line, text=text)
    spinner.start()
    return spinner


def spinner_stop(spinner):
    spinner.stop()
