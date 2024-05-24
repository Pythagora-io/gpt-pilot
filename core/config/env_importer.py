from os.path import dirname, exists, join

from dotenv import dotenv_values

from core.config import Config, LLMProvider, ProviderConfig, loader


def import_from_dotenv(new_config_path: str) -> bool:
    """
    Import configuration from old gpt-pilot .env file and save it to a new format.

    If the configuration is already loaded, does nothing. If the target file
    already exists, it's parsed as is (it's not overwritten).

    Otherwise, loads the values from `pilot/.env` file and creates a new configuration
    with the relevant settings.

    This intentionally DOES NOT load the .env variables into the current process
    environments, to avoid polluting it with old settings.

    :param new_config_path: Path to save the new configuration file.
    :return: True if the configuration was imported, False otherwise.
    """
    if loader.config_path or exists(new_config_path):
        # Config already exists, nothing to do
        return True

    env_path = join(dirname(__file__), "..", "..", "pilot", ".env")
    if not exists(env_path):
        return False

    values = dotenv_values(env_path)
    if not values:
        return False

    config = convert_config(values)

    with open(new_config_path, "w", encoding="utf-8") as fp:
        fp.write(config.model_dump_json(indent=2))

    return True


def convert_config(values: dict) -> Config:
    config = Config()

    for provider in LLMProvider:
        endpoint = values.get(f"{provider.value.upper()}_ENDPOINT")
        key = values.get(f"{provider.value.upper()}_API_KEY")

        if provider == LLMProvider.OPENAI:
            # OpenAI is also used for Azure and OpenRouter and local LLMs
            if endpoint is None:
                endpoint = values.get("AZURE_ENDPOINT")
            if endpoint is None:
                endpoint = values.get("OPENROUTER_ENDPOINT")

            if key is None:
                key = values.get("AZURE_API_KEY")
            if key is None:
                key = values.get("OPENROUTER_API_KEY")
                if key and endpoint is None:
                    endpoint = "https://openrouter.ai/api/v1/chat/completions"

        if endpoint or key and provider not in config.llm:
            config.llm[provider] = ProviderConfig()

        if endpoint:
            endpoint = endpoint.replace("chat/completions", "")
            config.llm[provider].base_url = endpoint
        if key:
            config.llm[provider].api_key = key

    model = values.get("MODEL_NAME")
    if model:
        provider = "openai"
        if "/" in model:
            provider, model = model.split("/", 1)

        try:
            agent_provider = LLMProvider(provider.upper())
        except ValueError:
            agent_provider = LLMProvider.OPENAI

        config.agent["default"].model = model
        config.agent["default"].provider = agent_provider

    ignore_paths = [p for p in values.get("IGNORE_PATHS", "").split(",") if p]
    if ignore_paths:
        config.fs.ignore_paths += ignore_paths
    return config
