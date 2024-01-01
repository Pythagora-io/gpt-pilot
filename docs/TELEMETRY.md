## Telemetry in GPT Pilot

At GPT Pilot, we are dedicated to improving your experience and the overall quality of our software. To achieve this, we gather anonymous telemetry data which helps us understand how the tool is being used and identify areas for improvement.

### What We Collect

The telemetry data we collect includes:

- **Total Runtime**: The total time GPT Pilot was active and running.
- **Command Runs**: How many commands were executed during a session.
- **Development Steps**: The number of development steps that were performed.
- **LLM Requests**: The number of LLM requests made.
- **User Inputs**: The number of times you provide input to the tool.
- **Operating System**: The operating system you are using (and Linux distro if applicable).
- **Python Version**: The version of Python you are using.
- **GPT Pilot Version**: The version of GPT Pilot you are using.
- **LLM Model**: LLM model used for the session.
- **Time**: How long it took to generate a project.

All the data points are listed in [pilot.utils.telemetry:Telemetry.clear_data()](../pilot/utils/telemetry.py).

### How We Use This Data

We use this data to:

- Monitor the performance and reliability of GPT Pilot.
- Understand usage patterns to guide our development and feature prioritization.
- Identify common workflows and improve the user experience.
- Ensure the scalability and efficiency of our language model interactions.

### How is this differentr from Dev-tools 

GPT Pilot : 

Type: Code completion tool using GPT or similar language model.
Functionality: Provides context-aware code suggestions using natural language understanding during coding.
Integration: Integrated into code editors or development environments.
Usage: Primarily used in the coding phase to speed up development.

Traditional Development Tools (e.g., Git, Jenkins, JIRA, etc.):

Type: Varied tools for different purposes in the software development lifecycle.
Functionality: Focus on collaboration, automation, project management, and quality assurance.
Integration: Used across the entire development lifecycle, from planning and coding to testing and deployment.

Key Differences:

Purpose:

GitHub Copilot is specifically designed for code completion during the coding phase.
Traditional development tools serve various purposes throughout the entire software development lifecycle.

Functionality:

Copilot uses AI to suggest code snippets based on context and patterns.
Traditional development tools provide functionalities such as version control, continuous integration, and project management.

Integration:

Copilot is integrated into code editors.
Traditional development tools are integrated into the broader development environment and workflow.

Usage:

Copilot is primarily used to speed up coding by suggesting code.
Traditional development tools are used for collaboration, automation, project management, and ensuring code quality.


### Your Privacy

Your privacy is important to us. The data collected is purely for internal analysis and will not be shared with third parties. No personal information is collected, and telemetry data is completely anonymized. We adhere to best practices in data security to protect this information.

### Opting Out

We believe in transparency and control. If you prefer not to send telemetry data, you can opt-out at any time by setting `telemetry.enabled` to `false` in your `~/.gpt-pilot/config.json` configuration file.

After you update this setting, GPT Pilot will no longer collect telemetry data from your machine.

### Questions and Feedback
If you have questions about our telemetry practices or would like to provide feedback, please open an issue in our repository, and we will be happy to engage with you.

Thank you for supporting GPT Pilot and helping us make it better for everyone.
