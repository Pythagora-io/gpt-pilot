import pytest

from core.llm.convo import Convo


def test_convo_constructor_without_content():
    convo = Convo()
    assert convo.messages == []


def test_convo_constructor_with_content():
    convo = Convo("Hello, world!")
    assert len(convo.messages) == 1
    assert convo.messages[0]["role"] == "system"
    assert convo.messages[0]["content"] == "Hello, world!"


def test_convo_constructor_with_whitespace_content():
    convo = Convo("  Hello, world!  ")
    assert len(convo.messages) == 1
    assert convo.messages[0]["role"] == "system"
    assert convo.messages[0]["content"] == "Hello, world!"


def test_add_unknown_role_raises_value_error():
    convo = Convo()
    with pytest.raises(ValueError) as excinfo:
        convo.add("unknown", "hello")
    assert str(excinfo.value) == "Unknown role: unknown"


def test_add_adds_message_with_role_and_content():
    convo = Convo()
    convo.add("user", "hello")
    assert convo.messages[0] == {"role": "user", "content": "hello"}


def test_add_adds_message_with_role_content_and_name():
    convo = Convo()
    convo.add("user", "hello", "Alice")
    assert convo.messages[0] == {"role": "user", "content": "hello", "name": "Alice"}


def test_add_dedents_string_content():
    convo = Convo()
    convo.add("user", "\n    hello\n    world\n")
    assert convo.messages[0]["content"] == "\nhello\nworld"


def test_add_forwards_dict_content():
    convo = Convo()
    convo.add("user", {"text": "hello"})
    assert convo.messages[0]["content"] == {"text": "hello"}


def test_system_adds_system_message():
    convo = Convo()
    convo.system("Hello, world!")
    assert convo.messages == [{"role": "system", "content": "Hello, world!"}]


def test_system_adds_system_message_with_name():
    convo = Convo()
    convo.system("Hello, world!", "System")
    assert convo.messages == [{"role": "system", "content": "Hello, world!", "name": "System"}]


def test_system_dedents_content():
    convo = Convo()
    convo.system("    Hello, world!")
    assert convo.messages == [{"role": "system", "content": "Hello, world!"}]


def test_system_preserves_lines_in_content():
    convo = Convo()
    convo.system("Hello,\nworld!")
    assert convo.messages == [{"role": "system", "content": "Hello,\nworld!"}]


def test_user_adds_user_message():
    convo = Convo()
    convo.user("Hello, World!")
    assert convo.messages[0] == {"role": "user", "content": "Hello, World!"}


def test_user_adds_user_message_with_name():
    convo = Convo()
    convo.user("Hello, World!", "John Doe")
    assert convo.messages[0] == {
        "role": "user",
        "content": "Hello, World!",
        "name": "John Doe",
    }


def test_user_raises_error_if_content_is_empty_string():
    convo = Convo()
    with pytest.raises(ValueError):
        convo.user("")


def test_user_raises_error_if_content_is_none():
    convo = Convo()
    with pytest.raises(ValueError):
        convo.user(None)


def test_assistant_adds_correct_message():
    convo = Convo()
    convo.assistant("Hello, world!")
    assert convo.messages == [{"role": "assistant", "content": "Hello, world!"}]


def test_assistant_dedents_content():
    convo = Convo()
    convo.assistant("    Hello, world!")
    assert convo.messages == [{"role": "assistant", "content": "Hello, world!"}]


def test_assistant_adds_name_if_provided():
    convo = Convo()
    convo.assistant("Hello, world!", "Geppetto")
    assert convo.messages == [{"role": "assistant", "content": "Hello, world!", "name": "Geppetto"}]


def test_assistant_returns_self():
    convo = Convo()
    result = convo.assistant("Hello, world!")
    assert result is convo


def test_function_message_added_correctly():
    convo = Convo()
    convo.function("Hello World")
    assert len(convo.messages) == 1
    assert convo.messages[0]["role"] == "function"
    assert convo.messages[0]["content"] == "Hello World"


def test_function_message_with_name_added_correctly():
    convo = Convo()
    convo.function("Hello World", name="Function1")
    assert len(convo.messages) == 1
    assert convo.messages[0]["role"] == "function"
    assert convo.messages[0]["content"] == "Hello World"
    assert convo.messages[0]["name"] == "Function1"


def test_function_message_content_dedented():
    convo = Convo()
    convo.function("  Hello World  ")
    assert len(convo.messages) == 1
    assert convo.messages[0]["role"] == "function"
    assert convo.messages[0]["content"] == "Hello World"


def test_function_message_return_convo_object():
    convo = Convo()
    result = convo.function("Hello World")
    assert isinstance(result, Convo)


def test_function_message_with_empty_content():
    convo = Convo()
    with pytest.raises(ValueError):
        convo.function("")


def test_function_message_with_non_string_content():
    convo = Convo()
    with pytest.raises(TypeError):
        convo.function(123)


def test_convo_fork():
    convo1 = Convo("Hello")
    convo1.user("Hello LLM!")
    convo1.assistant("Hello User!")
    convo2 = convo1.fork()
    assert convo1.messages == convo2.messages
    convo1.user("New message in convo1")
    assert convo1.messages != convo2.messages
    convo2.assistant("New message in convo2")
    assert convo1.messages != convo2.messages


def test_convo_fork_with_no_messages():
    convo1 = Convo()
    convo2 = convo1.fork()
    assert convo1.messages == convo2.messages
    convo1.user("New message in convo1")
    assert convo1.messages != convo2.messages
    convo2.assistant("New message in convo2")
    assert convo1.messages != convo2.messages


def test_convo_fork_with_multiple_messages():
    convo1 = Convo("Init")
    convo1.user("Hello!").assistant("Hi!").user("How are you?")
    convo2 = convo1.fork()
    assert convo1.messages == convo2.messages
    convo1.assistant("I'm good! How are you?")
    assert convo1.messages != convo2.messages
    convo2.assistant("I'm fine! How are you?")
    assert convo1.messages != convo2.messages


def test_after_with_empty_convos():
    convo1 = Convo()
    convo2 = Convo()
    new_convo = convo1.after(convo2)
    assert new_convo.messages == []


def test_after_with_no_common_messages():
    convo1 = Convo()
    convo1.user("Hello")
    convo2 = Convo()
    convo2.user("Hi")
    new_convo = convo1.after(convo2)
    assert new_convo.messages == convo1.messages


def test_after_with_some_common_messages():
    convo1 = Convo()
    convo1.user("Hello").assistant("How can I assist?")
    convo2 = convo1.fork()
    convo2.user("What's the weather?")
    new_convo = convo2.after(convo1)
    assert new_convo.messages == [{"role": "user", "content": "What's the weather?"}]


def test_after_with_all_common_messages():
    convo1 = Convo()
    convo1.user("Hello")
    convo2 = convo1.fork()
    new_convo = convo2.after(convo1)
    assert new_convo.messages == []


def test_after_with_more_messages_in_parent_convo():
    convo1 = Convo()
    convo1.user("Hello").assistant("How can I assist?").user("What's the weather?")
    convo2 = Convo()
    convo2.user("Hello").assistant("How can I assist?")
    new_convo = convo1.after(convo2)
    assert new_convo.messages == [{"role": "user", "content": "What's the weather?"}]


def test_last_empty_convo():
    convo = Convo()
    assert convo.last() is None


def test_last_single_message_convo():
    convo = Convo()
    convo.user("Hello")
    assert convo.last()["content"] == "Hello"


def test_last_multiple_messages_convo():
    convo = Convo()
    convo.user("Hello")
    convo.assistant("Hi")
    assert convo.last()["content"] == "Hi"


def test_last_after_fork():
    convo = Convo()
    convo.user("Hello")
    forked_convo = convo.fork()
    forked_convo.assistant("Hi")
    assert convo.last()["content"] == "Hello"
    assert forked_convo.last()["content"] == "Hi"


def test_last_after_deepcopy():
    from copy import deepcopy

    convo = Convo()
    convo.user("Hello")
    copied_convo = deepcopy(convo)
    copied_convo.assistant("Hi")
    assert convo.last()["content"] == "Hello"
    assert copied_convo.last()["content"] == "Hi"


def test_message_iterator():
    convo = Convo("hello").user("world")
    messages = []
    for message in convo:
        messages.append(message)
    assert messages == [
        {"role": "system", "content": "hello"},
        {"role": "user", "content": "world"},
    ]
