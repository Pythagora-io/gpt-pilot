# 🧑‍✈️ GPT-PILOT
This is our try to see how can GPT-4 be utilized to generate working apps and to my surprise, it works quite well.

The idea is that AI won't be able to (at least in the near future) create apps from scratch without the developer being involved. That's why we created an interactive tool that generates code but also requires the developer to check each step so that they can understand what's going on and so that the AI can have a better overview of the entire codebase.

Obviously, it still can't create any production-ready app but the general concept of how this could work is there.


# 🔎 Examples

Here are a couple of example apps GPT Pilot created by itself:

### Real-time chat app
- ▶️ [video of the app creation process](https://www.youtube.com/watch?v=5c2sZEgDcBg)
- 💻️ [Github repo](https://github.com/Pythagora-io/gpt-pilot-chat-app-demo)

![gpt-pilot demo chat app](https://github.com/Pythagora-io/gpt-pilot-demo-chat-app/assets/10895136/16445462-a667-44dc-a98c-12da6a798338)


### Markdown editor
- ▶️ [video of the app creation process](https://youtu.be/uZeA1iX9dgg)
- 💻️ [Github repo](https://github.com/Pythagora-io/gpt-pilot-demo-markdown-editor.git)

![gpt-pilot demo markdown editor](https://github.com/Pythagora-io/gpt-pilot-demo-chat-app/assets/10895136/a860ad49-1773-4960-a996-8797466de5ac)


### Timer app
- ▶️ [video of the app creation process](https://youtu.be/CMN3W18zfiE)
- 💻️ [Github repo](https://github.com/Pythagora-io/gpt-pilot-timer-app-demo)

![gpt-pilot demo markdown editor](https://github.com/Pythagora-io/gpt-pilot-demo-chat-app/assets/10895136/b61b8f4f-b873-43af-a0e9-15509d606dbc)

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
