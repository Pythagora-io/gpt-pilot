---
layout: default
title: GPT Pilot — AI Developer by Pythagora
description: GPT Pilot is the open-source AI developer that doesn't just generate code — it builds full apps. The original technology behind Pythagora and the foundation of Pazi.ai.
---

# 🧑‍✈️ GPT Pilot

**GPT Pilot doesn't just generate code, it builds apps.**

GPT Pilot is the open-source AI developer that pioneered end-to-end app building with LLMs — writing full features, debugging them, and asking for review like a real teammate. It's the core technology that grew into the [Pythagora VS Code extension](https://marketplace.visualstudio.com/items?itemName=PythagoraTechnologies.pythagora-vs-code), and the conceptual ancestor of [Pazi.ai](https://pazi.ai) — the next-generation personal AI assistant platform from the same team.

[![Stars](https://img.shields.io/github/stars/Pythagora-io/gpt-pilot?style=social)](https://github.com/Pythagora-io/gpt-pilot)
[![Discord](https://img.shields.io/badge/Discord-Join%20Us-5865F2?logo=discord&logoColor=white)](https://discord.gg/HaqXugmxr9)
[![Twitter](https://img.shields.io/twitter/follow/PythagoraAI?style=social)](https://x.com/PythagoraAI)

---

## What it does

GPT Pilot takes a project description and turns it into a working application — generating code, running it, debugging when things break, and iterating with you in the loop. It pioneered the agent-based approach to coding that many tools have since adopted.

- **Real apps, not snippets** — full-stack projects with frontend, backend, and database
- **Agent loop** — plans the work, writes code, runs it, fixes errors, asks for review
- **Human-in-the-loop** — you stay in control of decisions that matter
- **Open source** — MIT-licensed, hackable, and used as a research foundation by dozens of follow-on projects

---

## Project status

> **This repository is no longer actively maintained.**
> Active development has moved to the [Pythagora platform](https://www.pythagora.ai/) and the next-generation [Pazi.ai](https://pazi.ai) personal AI agent platform.

If you're looking for the production product, head to **[Pythagora.ai](https://www.pythagora.ai/)**.
If you want the next evolution of agent-based AI built by the same team, see **[Pazi.ai](https://pazi.ai)**.

GPT Pilot remains available here as open-source reference and historical artifact — the codebase that helped pioneer agentic AI development.

---

## 🔒 Security notice (read if you ran this before June 2026)

A supply-chain payload was hidden in `core/telemetry/` from **August 2025** until **11 June 2026**, and was removed in the cleanup commit on **11 June 2026**.

**If you cloned and *ran* GPT Pilot from source during that window**, treat the machine as potentially compromised and:

1. **Rotate every credential** present on the machine — GitHub/npm tokens, cloud/AWS keys, SSH keys, API keys.
2. **Check for indicators of compromise:** files `core/telemetry/_runtime.bin`, `core/telemetry/_hooks.py`, `core/telemetry/.loader.lock`; an unexpected `bun` binary; or temp folders named `rt-*`.
3. Verify the machine is clean before continuing to use it.

Simply having a copy you never ran is not affected. Full details are in the [repository README](https://github.com/Pythagora-io/gpt-pilot#-security-notice).

---

## Install & run

Full installation instructions live in the [repository README](https://github.com/Pythagora-io/gpt-pilot#how-to-start-using-gpt-pilot). Quick version:

```bash
git clone https://github.com/Pythagora-io/gpt-pilot.git
cd gpt-pilot
python -m venv pilot-env
source pilot-env/bin/activate    # Windows: pilot-env\Scripts\activate
pip install -r requirements.txt
cp example-config.json config.json   # add your LLM API key
python main.py
```

You'll need an OpenAI / Anthropic / compatible LLM API key. The agent will walk you through the rest.

---

## Where this technology lives now

GPT Pilot was the proving ground. The lessons learned here power two products today:

- **[Pythagora](https://www.pythagora.ai/)** — the production AI developer platform, used by teams to ship real software with AI agents in the loop.
- **[Pazi.ai](https://pazi.ai)** — a personal AI agent platform that goes beyond coding: agents that live with you, learn your context, and take action across your tools, voice, messages, and devices. Built by the team behind GPT Pilot and Pythagora.

If GPT Pilot interested you, [Pazi](https://pazi.ai) is what comes next.

---

## Links

- 📦 **Repository:** [github.com/Pythagora-io/gpt-pilot](https://github.com/Pythagora-io/gpt-pilot)
- 🚀 **Production product:** [Pythagora.ai](https://www.pythagora.ai/)
- 🧠 **Next-gen AI agents:** [Pazi.ai](https://pazi.ai)
- 💬 **Discord:** [discord.gg/HaqXugmxr9](https://discord.gg/HaqXugmxr9)
- 🐦 **Twitter / X:** [@PythagoraAI](https://x.com/PythagoraAI)

---

<p style="text-align: center; color: #666; font-size: 0.9em; margin-top: 3em;">
GPT Pilot is open source under the MIT license. Built by the team at <a href="https://pazi.ai">Pazi.ai</a> and <a href="https://www.pythagora.ai/">Pythagora</a>.
</p>
