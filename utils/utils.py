def print_message(msg, username):
    RESET = "\033[0m"
    TIME_COLOR = "\033[92m"
    USER_COLOR = "\033[94m"
    SELF_COLOR = "\033[97m"
    if msg['username'] == username:
        print(f"{TIME_COLOR}{msg['time']}{RESET} {SELF_COLOR}[{msg['username']}]{RESET}: {msg['message_content']}")
    else:
        print(f"{TIME_COLOR}{msg['time']}{RESET} {USER_COLOR}[{msg['username']}]{RESET}: {msg['message_content']}")