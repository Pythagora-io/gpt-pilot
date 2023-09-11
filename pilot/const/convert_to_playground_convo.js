let messages = {{messages}}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function fill_playground(messages) {
    let system_messages = messages.filter(msg => msg.role === 'system');
    if (system_messages.length > 0) {
        let system_message_textarea = document.querySelector('.chat-pg-instructions').querySelector('textarea');
        system_message_textarea.focus();
        system_message_textarea.value = '';
        document.execCommand("insertText", false, system_messages[0].content);
        await sleep(100);
    }

    // Remove all previous messages
    let remove_buttons = document.querySelectorAll('.chat-message-remove-button');
    for (let j = 0; j < 10; j++) {
        for (let i = 0; i < remove_buttons.length; i++) {
            let clickEvent = new Event('click', {
                'bubbles': true,
                'cancelable': true
            });
            remove_buttons[i].dispatchEvent(clickEvent);
        }
    }

    let other_messages = messages.filter(msg => msg.role !== 'system');

    for (let i = 0; i < other_messages.length; i++) {
        document.querySelector('.add-message').click()
        await sleep(100);
    }

    for (let i = 0; i < other_messages.length; i++) {
        let all_elements = document.querySelectorAll('.text-input-with-focus');
        let last_user_document = all_elements[i];
        
        textarea_to_fill = last_user_document.querySelector('textarea');
        textarea_to_fill.focus();
        document.execCommand("insertText", false, other_messages[i].content);
        await sleep(100);
    }
}

fill_playground(messages)