import subprocess
import os
import signal
import threading
import queue
import time

def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

def run_command(command, queue, pid_container):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, preexec_fn=os.setsid)
    pid_container[0] = process.pid
    t = threading.Thread(target=enqueue_output, args=(process.stdout, queue))
    t.daemon = True
    t.start()

def execute_command(command, timeout=5):
    q = queue.Queue()
    pid_container = [None]
    run_command(command, q, pid_container)
    output = ''
    start_time = time.time()

    while True:
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout:
            os.killpg(pid_container[0], signal.SIGKILL)
            break

        try:
            line = q.get_nowait()
        except queue.Empty:
            line = None

        if line:
            output += line

    return output[-2000:]