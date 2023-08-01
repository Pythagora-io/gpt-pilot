let messages = {{messages}}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function fill_playground(messages) {
    let system_messages = messages.filter(msg => msg.role === 'system');
    if (system_messages.length > 0) {
        let system_message_textarea = document.querySelector('.chat-pg-instructions').querySelector('textarea');
        system_message_textarea.focus();
        document.execCommand("insertText", false, system_messages[0].content);
        await sleep(100);
    }

    let other_messages = messages.filter(msg => msg.role !== 'system');

    for (let i = 0; i < other_messages.length - 1; i++) {
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