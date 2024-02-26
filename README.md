# 🧑‍✈️ GPT PILOT

<a href="https://trendshift.io/repositories/466" target="_blank"><img src="https://trendshift.io/api/badge/repositories/466" alt="Pythagora-io%2Fgpt-pilot | Trendshift" style="width: 250px; height: 55px; margin-right: 10px;" width="250" height="55"/></a>
### GPT Pilot is a true AI developer that writes code, debugs it, talks to you when it needs help, etc.

You specify what kind of app you want to build. Then, GPT Pilot asks clarifying questions, creates the product and technical requirements, sets up the environment, and **starts coding the app step by step, like in real life, while you oversee the development process**. It asks you to review each task it finishes or to help when it gets stuck. This way, GPT Pilot acts as a coder while you are a lead dev who reviews code and helps when needed.

---

<a href="vscode:extension/PythagoraTechnologies.gpt-pilot-vs-code" target="_blank"><img src="https://github.com/Pythagora-io/gpt-pilot/assets/10895136/5792143e-77c7-47dd-ad96-6902be1501cd" alt="Pythagora-io%2Fgpt-pilot | Trendshift" style="width: 185px; height: 55px;" width="185" height="55"/></a>

GPT Pilot is the core technology for the [VS Code extension](https://bit.ly/3IeZxp6) that aims to provide **the first real AI developer companion**. Not just an autocomplete or a helper for PR messages but rather a real AI developer that can write full features, debug them, talk to you about issues, ask for review, etc.

---

📫 If you would like to get updates on future releases or just get in touch, you [can add your email here](http://eepurl.com/iD6Mpo). 📬

---

<!-- TOC -->
* [🔌 Requirements](#-requirements)
* [🚦How to start using gpt-pilot?](#how-to-start-using-gpt-pilot)
    * [🐳 How to start gpt-pilot in docker?](#-how-to-start-gpt-pilot-in-docker)
* [🧑‍💻️ CLI arguments](#%EF%B8%8F-cli-arguments)
* [🔎 Examples](#-examples)
    * [Real-time chat app](#-real-time-chat-app)
    * [Markdown editor](#-markdown-editor)
    * [Timer app](#-timer-app)
* [🏛 Main pillars of GPT Pilot](#-main-pillars-of-gpt-pilot)
* [🏗 How GPT Pilot works?](#-how-gpt-pilot-works)
* [🕴How's GPT Pilot different from _Smol developer_ and _GPT engineer_?](#hows-gpt-pilot-different-from-smol-developer-and-gpt-engineer)
* [🍻 Contributing](#-contributing)
* [🔗 Connect with us](#-connect-with-us)
* [🌟 Star history](#-star-history)
<!-- TOC -->

---

GPT Pilot aims to research how much GPT-4 can be utilized to generate fully working, production-ready apps while the developer oversees the implementation.

**The main idea is that AI can write most of the code for an app (maybe 95%), but for the rest, 5%, a developer is and will be needed until we get full AGI**.

I've broken down the idea behind GPT Pilot and how it works in the following blog posts:

**[[Part 1/3] High-level concepts + GPT Pilot workflow until the coding part](https://blog.pythagora.ai/2023/08/23/430/)**

**_[[Part 2/3] GPT Pilot coding workflow](https://blog.pythagora.ai/2023/09/04/gpt-pilot-coding-workflow-part-2-3/)_**

**_[Part 3/3] Other important concepts and future plans (COMING UP)_**

---


<div align="center">

### **[👉 Examples of apps written by GPT Pilot 👈](#-examples)**

</div>

<br>

https://github.com/Pythagora-io/gpt-pilot/assets/10895136/0495631b-511e-451b-93d5-8a42acf22d3d

# 🔌 Requirements

- **Python 3.9+**
- **PostgreSQL** (Optional, default database is SQLite)
   - DB is needed for multiple reasons like continuing app development. If you have to stop at any point or the app crashes, go back to a specific step so that you can change some later steps in development, and easier debugging, in future we will add functionality to update project (change some things in existing project or add new features to the project and so on).


# 🚦How to start using gpt-pilot?
👉 If you are using VS Code as your IDE, the easiest way to start is by downloading [GPT Pilot VS Code extension](https://bit.ly/3IeZxp6). 👈

Otherwise, you can use the CLI tool.

After you have Python and (optionally) PostgreSQL installed, follow these steps:
1. `git clone https://github.com/Pythagora-io/gpt-pilot.git` (clone the repo)
2. `cd gpt-pilot`
3. `python -m venv pilot-env` (create a virtual environment)
4. `source pilot-env/bin/activate` (or on Windows `pilot-env\Scripts\activate`) (activate the virtual environment)
5. `pip install -r requirements.txt` (install the dependencies)
6. `cd pilot`
7. `mv .env.example .env` (or on Windows `copy .env.example .env`) (create the .env file)
8. Add your environment to the `.env` file:
   - LLM Provider (OpenAI/Azure/Openrouter)
   - Your API key
   - database settings: SQLite/PostgreSQL (to change from SQLite to PostgreSQL, just set `DATABASE_TYPE=postgres`)
   - optionally set IGNORE_PATHS for the folders which shouldn't be tracked by GPT Pilot in workspace, useful to ignore folders created by compilers (i.e. `IGNORE_PATHS=folder1,folder2,folder3`)
9. `python db_init.py` (initialize the database)
10. `python main.py` (start GPT Pilot)

After, this, you can just follow the instructions in the terminal.

All generated code will be stored in the folder `workspace` inside the folder named after the app name you enter upon starting the pilot.


## 🐳 How to start gpt-pilot in docker?
1. `git clone https://github.com/Pythagora-io/gpt-pilot.git` (clone the repo)
2. Update the `docker-compose.yml` environment variables, which can be done via `docker compose config`. If you wish to use a local model, please go to [https://localai.io/basics/getting_started/](https://localai.io/basics/getting_started/).
3. By default, GPT Pilot will read & write to `~/gpt-pilot-workspace` on your machine, you can also edit this in `docker-compose.yml`
4. run `docker compose build`. this will build a gpt-pilot container for you.
5. run `docker compose up`.
6. access the web terminal on `port 7681`
7. `python db_init.py` (initialize the database)
8. `python main.py` (start GPT Pilot)

This will start two containers, one being a new image built by the `Dockerfile` and a Postgres database. The new image also has [ttyd](https://github.com/tsl0922/ttyd) installed so that you can easily interact with gpt-pilot. Node is also installed on the image and port 3000 is exposed.


# 🧑‍💻️ CLI arguments

## `app_type` and `name`
If not provided, the ProductOwner will ask for these values:

`app_type` is used as a hint to the LLM as to what kind of architecture, language options and conventions would apply. If not provided, `prompts.prompts.ask_for_app_type()` will ask for it.

See `const.common.APP_TYPES`: 'Web App', 'Script', 'Mobile App', 'Chrome Extension'


## `app_id` and `workspace`
Continue working on an existing app using **`app_id`**
```bash
python main.py app_id=<ID_OF_THE_APP>
```

_or_ **`workspace`** path:

```bash
python main.py workspace=<PATH_TO_PROJECT_WORKSPACE>
```

Each user can have their own workspace path for each App.


## `user_id`, `email`, and `password`
These values will be saved to the User table in the DB.

```bash
python main.py user_id=me_at_work
```

If not specified, `user_id` defaults to the OS username but can be provided explicitly if your OS username differs from your GitHub or work username. This value is used to load the `App` config when the `workspace` arg is provided.

If not specified `email` will be parsed from `~/.gitconfig` if the file exists.

See also [What's the purpose of arguments.password / User.password?](https://github.com/Pythagora-io/gpt-pilot/discussions/55)


## `step`
Continue working on an existing app from a specific **`step`** (eg: `user_tasks`)
```bash
python main.py app_id=<ID_OF_THE_APP> step=<STEP_FROM_CONST_COMMON>
```


## `skip_until_dev_step`
Continue working on an existing app from a specific **development step**
```bash
python main.py app_id=<ID_OF_THE_APP> skip_until_dev_step=<DEV_STEP>
```
This is basically the same as `step` but during the development process. If you want to play around with gpt-pilot, this is likely the flag you will often use.
<br>

Erase all development steps previously done and continue working on an existing app from the start of development.

```bash
python main.py app_id=<ID_OF_THE_APP> skip_until_dev_step=0
```

## `theme`
```bash
python main.py theme=light
```

![屏幕截图 2023-10-15 103907](https://github.com/Pythagora-io/gpt-pilot/assets/138990495/c3d08f21-7e3b-4ee4-981f-281d1c97149e)
```bash
python main.py theme=dark
```
- Dark mode.
![屏幕截图 2023-10-15 104120](https://github.com/Pythagora-io/gpt-pilot/assets/138990495/942cd1c9-b774-498e-b72a-677b01be1ac3)


## `delete_unrelated_steps`


## `update_files_before_start`



# 🔎 Examples
### Backend system for billing, admin, and user management
- 💬 [Full initial prompt + additional features prompts](https://github.com/Pythagora-io/credit-based-backend-gpt-pilot-example/tree/main/prompts)
- ▶️ [Video overview of app features](https://youtu.be/-OB6BJKADEo)
- 💻️ [GitHub repo](https://github.com/Pythagora-io/credit-based-backend-gpt-pilot-example)
- 📊 Stats:
  - **3185** lines of code
  - **104** files
  - **~3** days of work

### SQLite db analytics app
- 💬 [All prompts used (initial and for additional features)](https://github.com/Pythagora-io/gpt-pilot-sqlite-analysis-tool/tree/main/prompts)
- ▶️ [Video overview of app features](https://youtu.be/7t-Q2e7QsbE)
- 💻️ [GitHub repo](https://github.com/Pythagora-io/gpt-pilot-sqlite-analysis-tool)
- 📊 Stats:
  - **730** lines of code
  - **9** files
  - **6** hours of work

## Simple Examples
### 📱 Real-time chat app
- 💬 Prompt: `A simple chat app with real-time communication`
- ▶️ [Video of the app creation process](https://youtu.be/bUj9DbMRYhA)
- 💻️ [GitHub repo](https://github.com/Pythagora-io/gpt-pilot-chat-app-demo)


### 📝 Markdown editor
- 💬 Prompt: `Build a simple markdown editor using HTML, CSS, and JavaScript. Allow users to input markdown text and display the formatted output in real-time.`
- ▶️ [Video of the app creation process](https://youtu.be/uZeA1iX9dgg)
- 💻️ [GitHub repo](https://github.com/Pythagora-io/gpt-pilot-demo-markdown-editor.git)


### ⏱️ Timer app
- 💬 Prompt: `Create a simple timer app using HTML, CSS, and JavaScript that allows users to set a countdown timer and receive an alert when the time is up.`
- ▶️ [Video of the app creation process](https://youtu.be/CMN3W18zfiE)
- 💻️ [GitHub repo](https://github.com/Pythagora-io/gpt-pilot-timer-app-demo)

<br>

# 🏗 How GPT Pilot works?
Here are the steps GPT Pilot takes to create an app:

![GPT Pilot workflow](https://github.com/Pythagora-io/gpt-pilot/assets/10895136/d89ba1d4-1208-4b7f-b3d4-76e3ccea584e)

1. You enter the app name and the description.
2. **Product Owner agent** asks a couple of questions to understand the requirements better.
3. **Product Owner agent** writes user stories and asks you if they are all correct (this helps it create code later on).
4. **Architect agent** writes up technologies that will be used for the app.
5. **DevOps agent** checks if all technologies are installed on the machine and installs them if not.
6. **Tech Lead agent** writes up development tasks that the Developer must implement. This is an important part because, for each step, the Tech Lead needs to specify how the user (real-world developer) can review if the task is done (e.g. open localhost:3000 and do something).
7. **Developer agent** takes each task and writes up what needs to be done to implement it. The description is in human-readable form.
8. Finally, **Code Monkey agent** takes the Developer's description and the existing file and implements the changes. We realized this works much better than giving it to the Developer right away to implement changes.

For more details on the roles of agents employed by GPT Pilot, please take a look at [AGENTS.md](https://github.com/Pythagora-io/gpt-pilot/blob/main/pilot/helpers/agents/AGENTS.md)

![GPT Pilot Coding Workflow](https://github.com/Pythagora-io/gpt-pilot/assets/10895136/53ea246c-cefe-401c-8ba0-8e4dd49c987b)


<br>

# 🕴How's GPT Pilot different from _Smol developer_ and _GPT engineer_?

- **GPT Pilot works with the developer to create a fully working production-ready app** - I don't think AI can (at least in the near future) create apps without a developer being involved. So, **GPT Pilot codes the app step by step** just like a developer would in real life. This way, it can debug issues as they arise throughout the development process. If it gets stuck, you, the developer in charge, can review the code and fix the issue. Other similar tools give you the entire codebase at once - this way, bugs are much harder to fix for AI and for you as a developer.
  <br><br>
- **Works at scale** - GPT Pilot isn't meant to create simple apps but rather so it can work at any scale. It has mechanisms that filter out the code, so in each LLM conversation, it doesn't need to store the entire codebase in context, but it shows the LLM only the relevant code for the current task it's working on. Once an app is finished, you can continue working on it by writing instructions on what feature you want to add.

# 🍻 Contributing
If you are interested in contributing to GPT Pilot, I would be more than happy to have you on board and also help you get started. Feel free to ping [zvonimir@pythagora.ai](mailto:zvonimir@pythagora.ai), and I'll help you get started.

## 🔬️ Research
Since this is a research project, there are many areas that need to be researched on both practical and theoretical levels. We're happy to hear how the entire GPT Pilot concept can be improved. For example, maybe it would work better if we structured functional requirements differently, or maybe technical requirements need to be specified in a different way.

## 🖥 Development
Other than the research, GPT Pilot needs to be debugged to work in different scenarios. For example, we realized that the quality of the code generated is very sensitive to the size of the development task. When the task is too broad, the code has too many bugs that are hard to fix, but when the development task is too narrow, GPT also seems to struggle in getting the task implemented into the existing code.

## 📊 Telemetry
To improve GPT Pilot, we are tracking some events from which you can opt out at any time. You can read more about it [here](./docs/TELEMETRY.md).

# 🔗 Connect with us
🌟 As an open-source tool, it would mean the world to us if you starred the GPT-pilot repo 🌟

💬 Join [the Discord server](https://discord.gg/HaqXugmxr9) to get in touch.


# 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Pythagora-io/gpt-pilot&type=Date)](https://star-history.com/#Pythagora-io/gpt-pilot&Date)
