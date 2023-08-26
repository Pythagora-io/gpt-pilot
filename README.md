# 🧑‍✈️ GPT PILOT
### GPT Pilot codes the entire app as you oversee the code being written

---

This is a research project to see how can GPT-4 be utilized to generate fully working, production-ready, apps. **The main idea is that AI can write most of the code for an app (maybe 95%) but for the rest 5%, a developer is and will be needed until we get full AGI**.

I've broken down the idea behind GPT Pilot and how it works in the following blog posts:

**[[Part 1/3] High-level concepts + GPT Pilot workflow until the coding part](https://blog.pythagora.ai/2023/08/23/430/)**

**_[Part 2/3] GPT Pilot coding workflow (COMING UP)_**

**_[Part 3/3] Other important concepts and future plans (COMING UP)_**

---

### **[👉 Examples of apps written by GPT Pilot can be found here 👈](#-examples)**

<br>

https://github.com/Pythagora-io/gpt-pilot/assets/10895136/0495631b-511e-451b-93d5-8a42acf22d3d

<br>

## Main pillars of GPT Pilot:
1. For AI to create a fully working app, **a developer needs to be involved** in the process of app creation. They need to be able to change the code at any moment and GPT Pilot needs to continue working with those changes (eg. add an API key or fix an issue if an AI gets stuck) <br><br>
2. **The app needs to be written step by step as a developer would write it** - Let's say you want to create a simple app and you know everything you need to code and have the entire architecture in your head. Even then, you won't code it out entirely, then run it for the first time and debug all the issues at once. Rather, you will implement something simple, like add routes, run it, see how it works, and then move on to the next task. This way, you can debug issues as they arise. The same should be in the case when AI codes. It will make mistakes for sure so in order for it to have an easier time debugging issues and for the developer to understand what is happening, the AI shouldn't just spit out the entire codebase at once. Rather, the app should be developed step by step just like a developer would code it - eg. setup routes, add database connection, etc. <br><br>
3. **The approach needs to be scalable** so that AI can create a production ready app
   1. **Context rewinding** - for solving each development task, the context size of the first message to the LLM has to be relatively the same. For example, the context size of the first LLM message while implementing development task #5 has to be more or less the same as the first message while developing task #50. Because of this, the conversation needs to be rewound to the first message upon each task. [See the diagram here](https://blogpythagora.files.wordpress.com/2023/08/pythagora-product-development-frame-3-1.jpg?w=1714).
   2. **Recursive conversations** are LLM conversations that are set up in a way that they can be used “recursively”. For example, if GPT Pilot detects an error, it needs to debug it but let’s say that, during the debugging process, another error happens. Then, GPT Pilot needs to stop debugging the first issue, fix the second one, and then get back to fixing the first issue. This is a very important concept that, I believe, needs to work to make AI build large and scalable apps by itself. It works by rewinding the context and explaining each error in the recursion separately. Once the deepest level error is fixed, we move up in the recursion and continue fixing that error. We do this until the entire recursion is completed. 
   3. **TDD (Test Driven Development)** - for GPT Pilot to be able to scale the codebase, it will need to be able to create new code without breaking previously written code. There is no better way to do this than working with TDD methodology. For each code that GPT Pilot writes, it needs to write tests that check if the code works as intended so that whenever new changes are made, all previous tests can be run.

The idea is that AI won't be able to (at least in the near future) create apps from scratch without the developer being involved. That's why we created an interactive tool that generates code but also requires the developer to check each step so that they can understand what's going on and so that the AI can have a better overview of the entire codebase.

Obviously, it still can't create any production-ready app but the general concept of how this could work is there.

# 🚦How to start using gpt-pilot?
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

# 🔎 Examples

Here are a couple of example apps GPT Pilot created by itself:

### Real-time chat app
- 💬 Prompt: `A simple chat app with real time communication`
- ▶️ [Video of the app creation process](https://youtu.be/bUj9DbMRYhA)
- 💻️ [Github repo](https://github.com/Pythagora-io/gpt-pilot-chat-app-demo)

<p align="left">
  <img src="https://github.com/Pythagora-io/gpt-pilot/assets/10895136/85bc705c-be88-4ca1-9a3b-033700b97a22" alt="gpt-pilot demo chat app" width="500px"/>
</p>


### Markdown editor
- 💬 Prompt: `Build a simple markdown editor using HTML, CSS, and JavaScript. Allow users to input markdown text and display the formatted output in real-time.`
- ▶️ [Video of the app creation process](https://youtu.be/uZeA1iX9dgg)
- 💻️ [Github repo](https://github.com/Pythagora-io/gpt-pilot-demo-markdown-editor.git)

<p align="left">
  <img src="https://github.com/Pythagora-io/gpt-pilot/assets/10895136/dbe1ccc3-b126-4df0-bddb-a524d6a386a8" alt="gpt-pilot demo markdown editor" width="500px"/>
</p>


### Timer app
- 💬 Prompt: `Create a simple timer app using HTML, CSS, and JavaScript that allows users to set a countdown timer and receive an alert when the time is up.`
- ▶️ [Video of the app creation process](https://youtu.be/CMN3W18zfiE)
- 💻️ [Github repo](https://github.com/Pythagora-io/gpt-pilot-timer-app-demo)

<p align="left">
  <img src="https://github.com/Pythagora-io/gpt-pilot/assets/10895136/93bed40b-b769-4c8b-b16d-b80fb6fc73e0" alt="gpt-pilot demo markdown editor" width="500px"/>
</p>

# 🏗 How GPT Pilot works?
Here are the steps GPT Pilot takes to create an app:

![GPT Pilot workflow](https://github.com/Pythagora-io/gpt-pilot/assets/10895136/d89ba1d4-1208-4b7f-b3d4-76e3ccea584e)

1. You enter the app name and the description
2. **Product Owner agent** asks a couple of questions to understand the requirements better
3. **Product Owner agent** writes user stories and asks you if they are all correct (this helps it create code later on)
4. **Architect agent** writes up technologies that will be used for the app
5. **DevOps agent** checks if all technologies are installed on the machine and installs them if they are not
6. **Tech Lead agent** writes up development tasks that Developer will need to implement. This is an important part because, for each step, Tech Lead needs to specify how the user (real world developer) can review if the task is done (eg. open localhost:3000 and do something)
7. **Developer agent** takes each task and writes up what needs to be done to implement it. The description is in human readable form.
8. Finally, **Code Monkey agent** takes the Developer's description and the currently implement file and implements the changes into it. We realized this works much better than giving it to Developer right away to implement changes.

![GPT Pilot Coding Workflow](https://github.com/Pythagora-io/gpt-pilot/assets/10895136/54a8ec24-a2ea-43a6-a494-03139d4e43f5)

<br>

# 🕴How's GPT Pilot different from _Smol developer_ and _GPT engineer_?
- **Human developer is involved throughout the process** - I don't think that AI can't (at least in the near future) create apps without a developer being involved. Also, I think it's hard for a developer to get into a big codebase and try debugging it. That's why my idea was for AI to develop the app step by step where each step is reviewed by the developer. If you want to change some code yourself, you can just change it and GPT Pilot will continue developing on top of those changes.
  <br><br>
- **Continuous development loops** - The goal behind this project was to see how we can create recursive conversations with GPT so that it can debug any issue and implement any feature. For example, after the app is generated, you can always add more instructions about what you want to implement or debug. I wanted to see if this can be so flexible that, regardless of the app's size, it can just iterate and build bigger and bigger apps
  <br><br>
- **Auto debugging** - when it detects an error, it debugs it by itself. I still haven't implemented writing automated tests which should make this fully autonomous but for now, you can input the error that's happening (eg. within a UI) and GPT Pilot will debug it from there. The plan is to make it write automated tests in Cypress as well so that it can test it by itself and debug without the developer's explanation.

# 🔗 Connect with us
🌟 As an open source tool, it would mean the world to us if you starred the GPT-pilot repo 🌟
<br><br>
<br><br>

<br><br>
