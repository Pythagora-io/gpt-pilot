import builtins
from helpers.ipc import IPCClient
from const.ipc import MESSAGE_TYPE, LOCAL_IGNORE_MESSAGE_TYPES


def get_custom_print(args):
    built_in_print = builtins.print

    def print_to_external_process(*args, **kwargs):
        # message = " ".join(map(str, args))
        message = args[0]

        if 'type' not in kwargs:
            kwargs['type'] = 'verbose'
        elif kwargs['type'] == MESSAGE_TYPE['local']:
            local_print(*args, **kwargs)
            return

        ipc_client_instance.send({
            'type': MESSAGE_TYPE[kwargs['type']],
            'content': message,
        })
        if kwargs['type'] == MESSAGE_TYPE['user_input_request']:
            return ipc_client_instance.listen()

    def local_print(*args, **kwargs):
        message = " ".join(map(str, args))
        if 'type' in kwargs:
            if kwargs['type'] in LOCAL_IGNORE_MESSAGE_TYPES:
                return
            del kwargs['type']

        built_in_print(message, **kwargs)

    ipc_client_instance = None
    if '--external-log-process-port' in args:
        ipc_client_instance = IPCClient(args['--external-log-process-port'])
        return print_to_external_process, ipc_client_instance
    else:
        return local_print, ipc_client_instance
