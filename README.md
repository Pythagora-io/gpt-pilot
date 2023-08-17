# 🧑‍✈️ GPT-PILOT
This is our try to see how can GPT-4 be utilized to generate working apps and to my surprise, it works quite well.

The idea is that AI won't be able to (at least in the near future) create apps from scratch without the developer being involved. That's why we created an interactive tool that generates code but also requires the developer to check each step so that they can understand what's going on and so that the AI can have a better overview of the entire codebase.

Obviously, it still can't create any production-ready app but the general concept of how this could work is there.


# 🔎 Examples

Here are a couple of example apps GPT Pilot created by itself:

### Real-time chat app
- 💬 Prompt: `A simple chat app with real time communication`
- ▶️ [video of the app creation process](https://youtu.be/bUj9DbMRYhA)
- 💻️ [Github repo](https://github.com/Pythagora-io/gpt-pilot-chat-app-demo)

![gpt-pilot demo chat app](https://github.com/Pythagora-io/gpt-pilot/assets/10895136/85bc705c-be88-4ca1-9a3b-033700b97a22)



### Markdown editor
- 💬 Prompt: `Build a simple markdown editor using HTML, CSS, and JavaScript. Allow users to input markdown text and display the formatted output in real-time.`
- ▶️ [video of the app creation process](https://youtu.be/uZeA1iX9dgg)
- 💻️ [Github repo](https://github.com/Pythagora-io/gpt-pilot-demo-markdown-editor.git)

![gpt-pilot demo markdown editor](https://github.com/Pythagora-io/gpt-pilot/assets/10895136/dbe1ccc3-b126-4df0-bddb-a524d6a386a8)


### Timer app
- 💬 Prompt: `Create a simple timer app using HTML, CSS, and JavaScript that allows users to set a countdown timer and receive an alert when the time is up.`
- ▶️ [video of the app creation process](https://youtu.be/CMN3W18zfiE)
- 💻️ [Github repo](https://github.com/Pythagora-io/gpt-pilot-timer-app-demo)

![gpt-pilot demo markdown editor](https://github.com/Pythagora-io/gpt-pilot/assets/10895136/93bed40b-b769-4c8b-b16d-b80fb6fc73e0)

<br>

## 🚦How to start using gpt-pilot?
1. Clone the repo
2. `cd gpt-pilot`
3. `python -m venv pilot-env`
4. `source pilot-env/bin/activate`
3. `pip install -r requirements.txt`
4. `cd pilot`
5. `mv .env.example .env`
6. Add your OpenAI API key and the database info to the `.env` file
7. `python main.py`

After, this, you can just follow the instructions in the terminal.

All generated code will be stored in the folder `workspace` inside the folder named after the app name you enter upon starting the pilot.

<br>

# 🧑‍💻️ Other arguments
- continue working on an existing app
```bash
python main.py app_id=<ID_OF_THE_APP>
```

- continue working on an existing app from a specific step
```bash
python main.py app_id=<ID_OF_THE_APP> step=<STEP_FROM_CONST_COMMON>
```

- continue working on an existing app from a specific development step
```bash
python main.py app_id=<ID_OF_THE_APP> skip_until_dev_step=<DEV_STEP>
```
This is basically the same as `step` but during the actual development process. If you want to play around with gpt-pilot, this is likely the flag you will often use

<br>

# 🕴How's GPT Pilot different from _Smol developer_ and _GPT engineer_?
- **Human developer is involved throughout the process** - I don't think that AI can't (at least in the near future) create apps without a developer being involved. Also, I think it's hard for a developer to get into a big codebase and try debugging it. That's why my idea was for AI to develop the app step by step where each step is reviewed by the developer. If you want to change some code yourself, you can just change it and GPT Pilot will continue developing on top of those changes.
  <br><br>
- **Continuous development loops** - The goal behind this project was to see how we can create recursive conversations with GPT so that it can debug any issue and implement any feature. For example, after the app is generated, you can always add more instructions about what you want to implement or debug. I wanted to see if this can be so flexible that, regardless of the app's size, it can just iterate and build bigger and bigger apps
  <br><br>
- **Auto debugging** - when it detects an error, it debugs it by itself. I still haven't implemented writing automated tests which should make this fully autonomous but for now, you can input the error that's happening (eg. within a UI) and GPT Pilot will debug it from there. The plan is to make it write automated tests in Cypress as well so that it can test it by itself and debug without the developer's explanation.

# 🏗 How GPT Pilot works?
Here are the steps GPT Pilot takes to create an app:
1. You enter the app name and the description
2. **Product Owner agent** asks a couple of questions to understand the requirements better
3. **Product Owner agent** writes user stories and asks you if they are all correct (this helps it create code later on)
4. **Architect agent** writes up technologies that will be used for the app
5. **DevOps agent** checks if all technologies are installed on the machine and installs them if they are not
6. **Tech Lead agent** writes up development tasks that Developer will need to implement. This is an important part because, for each step, Tech Lead needs to specify how the user (real world developer) can review if the task is done (eg. open localhost:3000 and do something)
7. **Developer agent** takes each task and writes up what needs to be done to implement it. The description is in human readable form.
8. Finally, **Code Monkey agent** takes the Developer's description and the currently implement file and implements the changes into it. We realized this works much better than giving it to Developer right away to implement changes.

# 🔗 Connect with us
🌟 As an open source tool, it would mean the world to us if you starred the GPT-pilot repo 🌟
<br><br>
<br><br>

<br><br>
