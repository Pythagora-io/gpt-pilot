from enum import Enum
from os.path import abspath, dirname, isdir, join
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing_extensions import Annotated

ROOT_DIR = abspath(join(dirname(__file__), "..", ".."))
DEFAULT_IGNORE_PATHS = [
    ".git",
    ".gpt-pilot",
    ".idea",
    ".vscode",
    ".next",
    ".DS_Store",
    "__pycache__",
    "site-packages",
    "node_modules",
    "package-lock.json",
    "venv",
    ".venv",
    "dist",
    "build",
    "target",
    "*.min.js",
    "*.min.css",
    "*.svg",
    "*.csv",
    "*.log",
    "go.sum",
    "migration_lock.toml",
]
IGNORE_SIZE_THRESHOLD = 50000  # 50K+ files are ignored by default

# Agents with sane setup in the default configuration
DEFAULT_AGENT_NAME = "default"
CODE_MONKEY_AGENT_NAME = "CodeMonkey"
CODE_REVIEW_AGENT_NAME = "CodeMonkey.code_review"
DESCRIBE_FILES_AGENT_NAME = "CodeMonkey.describe_files"
CHECK_LOGS_AGENT_NAME = "BugHunter.check_logs"
PARSE_TASK_AGENT_NAME = "Developer.parse_task"
TASK_BREAKDOWN_AGENT_NAME = "Developer.breakdown_current_task"
TROUBLESHOOTER_BUG_REPORT = "Troubleshooter.generate_bug_report"
TROUBLESHOOTER_GET_RUN_COMMAND = "Troubleshooter.get_run_command"
TECH_LEAD_PLANNING = "TechLead.plan_epic"
TECH_LEAD_EPIC_BREAKDOWN = "TechLead.epic_breakdown"
SPEC_WRITER_AGENT_NAME = "SpecWriter"
GET_RELEVANT_FILES_AGENT_NAME = "get_relevant_files"
FRONTEND_AGENT_NAME = "Frontend"

# Endpoint for the external documentation
EXTERNAL_DOCUMENTATION_API = "http://docs-pythagora-io-439719575.us-east-1.elb.amazonaws.com"


class _StrictModel(BaseModel):
    """
    Pydantic parser configuration options.
    """

    model_config = ConfigDict(
        extra="forbid",
    )


class LLMProvider(str, Enum):
    """
    Supported LLM providers.
    """

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    LM_STUDIO = "lm-studio"
    AZURE = "azure"


class UIAdapter(str, Enum):
    """
    Supported UI adapters.
    """

    PLAIN = "plain"
    IPC_CLIENT = "ipc-client"
    VIRTUAL = "virtual"


class ProviderConfig(_StrictModel):
    """
    LLM provider configuration.
    """

    base_url: Optional[str] = Field(
        None,
        description="Base URL for the provider's API (if different from the provider default)",
    )
    api_key: Optional[str] = Field(
        None,
        description="API key to use for authentication (if not set, provider uses default from environment variable)",
    )
    connect_timeout: float = Field(
        default=60.0,
        description="Timeout (in seconds) for connecting to the provider's API",
        ge=0.0,
    )
    read_timeout: float = Field(
        default=60.0,
        description="Timeout (in seconds) for receiving a new chunk of data from the response stream",
        ge=0.0,
    )
    extra: Optional[dict[str, Any]] = Field(
        None,
        description="Extra provider-specific configuration",
    )


class AgentLLMConfig(_StrictModel):
    """
    Configuration for the various LLMs used by Pythagora.

    Each Agent has an LLM provider, from the Enum LLMProvider. If
    AgentLLMConfig is not specified, default will be used.
    """

    provider: Optional[LLMProvider] = Field(default=LLMProvider.OPENAI, description="LLM provider")
    model: str = Field(description="Model to use", default="gpt-4o-2024-05-13")
    temperature: float = Field(
        default=0.5,
        description="Temperature to use for sampling",
        ge=0.0,
        le=1.0,
    )


class LLMConfig(_StrictModel):
    """
    Complete agent-specific configuration for an LLM.
    """

    provider: LLMProvider = LLMProvider.OPENAI
    model: str = Field(description="Model to use")
    base_url: Optional[str] = Field(
        None,
        description="Base URL for the provider's API (if different from the provider default)",
    )
    api_key: Optional[str] = Field(
        None,
        description="API key to use for authentication (if not set, provider uses default from environment variable)",
    )
    temperature: float = Field(
        default=0.5,
        description="Temperature to use for sampling",
        ge=0.0,
        le=1.0,
    )
    connect_timeout: float = Field(
        default=60.0,
        description="Timeout (in seconds) for connecting to the provider's API",
        ge=0.0,
    )
    read_timeout: float = Field(
        default=60.0,
        description="Timeout (in seconds) for receiving a new chunk of data from the response stream",
        ge=0.0,
    )
    extra: Optional[dict[str, Any]] = Field(
        None,
        description="Extra provider-specific configuration",
    )

    @classmethod
    def from_provider_and_agent_configs(cls, provider: ProviderConfig, agent: AgentLLMConfig):
        return cls(
            provider=agent.provider,
            model=agent.model,
            base_url=provider.base_url,
            api_key=provider.api_key,
            temperature=agent.temperature,
            connect_timeout=provider.connect_timeout,
            read_timeout=provider.read_timeout,
            extra=provider.extra,
        )


class PromptConfig(_StrictModel):
    """
    Configuration for prompt templates:
    """

    paths: list[str] = Field(
        [join(ROOT_DIR, "core", "prompts")],
        description="List of directories to search for prompt templates",
    )

    @field_validator("paths")
    @classmethod
    def validate_paths(cls, v: list[str]) -> list[str]:
        for path in v:
            if not isdir(path):
                raise ValueError(f"Invalid prompt path: {path}")
        return v


class LogConfig(_StrictModel):
    """
    Configuration for logging.
    """

    level: str = Field(
        "DEBUG",
        description="Logging level",
        pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )
    format: str = Field(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        description="Logging format",
    )
    output: Optional[str] = Field(
        "pythagora.log",
        description="Output file for logs (if not specified, logs are printed to stderr)",
    )


class DBConfig(_StrictModel):
    """
    Configuration for database connections.

    Supported URL schemes:

    * sqlite+aiosqlite: SQLite database using the aiosqlite driver
    """

    url: str = Field(
        "sqlite+aiosqlite:///data/database/pythagora.db",
        description="Database connection URL",
    )
    debug_sql: bool = Field(False, description="Log all SQL queries to the console")

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: str) -> str:
        if v.startswith("sqlite+aiosqlite://"):
            return v
        if v.startswith("postgresql+asyncpg://"):
            try:
                import asyncpg  # noqa: F401
            except ImportError:
                raise ValueError("To use PostgreSQL database, please install `asyncpg` and `psycopg2` packages")
            return v
        raise ValueError(f"Unsupported database URL scheme in: {v}")


class PlainUIConfig(_StrictModel):
    """
    Configuration for plaintext console UI.
    """

    type: Literal[UIAdapter.PLAIN] = UIAdapter.PLAIN


class LocalIPCConfig(_StrictModel):
    """
    Configuration for VSCode extension IPC client.
    """

    type: Literal[UIAdapter.IPC_CLIENT] = UIAdapter.IPC_CLIENT
    host: str = "localhost"
    port: int = 8125


class VirtualUIConfig(_StrictModel):
    """
    Configuration for the virtual UI.
    """

    type: Literal[UIAdapter.VIRTUAL] = UIAdapter.VIRTUAL
    inputs: list[Any]


UIConfig = Annotated[
    Union[PlainUIConfig, LocalIPCConfig, VirtualUIConfig],
    Field(discriminator="type"),
]


class FileSystemType(str, Enum):
    """
    Supported filesystem types.
    """

    MEMORY = "memory"
    LOCAL = "local"


class FileSystemConfig(_StrictModel):
    """
    Configuration for project workspace.
    """

    type: Literal[FileSystemType.LOCAL] = FileSystemType.LOCAL
    workspace_root: str = Field(
        join(ROOT_DIR, "workspace"),
        description="Workspace directory containing all the projects",
    )
    ignore_paths: list[str] = Field(
        DEFAULT_IGNORE_PATHS,
        description="List of paths to ignore when scanning for files and folders",
    )
    ignore_size_threshold: int = Field(
        IGNORE_SIZE_THRESHOLD,
        description="Files larger than this size should be ignored",
    )


class Config(_StrictModel):
    """
    Pythagora Core configuration
    """

    llm: dict[LLMProvider, ProviderConfig] = Field(
        default={
            LLMProvider.OPENAI: ProviderConfig(),
            LLMProvider.ANTHROPIC: ProviderConfig(),
        }
    )
    agent: dict[str, AgentLLMConfig] = Field(
        default={
            DEFAULT_AGENT_NAME: AgentLLMConfig(),
            CHECK_LOGS_AGENT_NAME: AgentLLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-sonnet-20241022",
                temperature=0.5,
            ),
            CODE_MONKEY_AGENT_NAME: AgentLLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-sonnet-20241022",
                temperature=0.0,
            ),
            CODE_REVIEW_AGENT_NAME: AgentLLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-sonnet-20240620",
                temperature=0.0,
            ),
            DESCRIBE_FILES_AGENT_NAME: AgentLLMConfig(
                provider=LLMProvider.OPENAI,
                model="gpt-4o-mini-2024-07-18",
                temperature=0.0,
            ),
            FRONTEND_AGENT_NAME: AgentLLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-sonnet-20241022",
                temperature=0.0,
            ),
            GET_RELEVANT_FILES_AGENT_NAME: AgentLLMConfig(
                provider=LLMProvider.OPENAI,
                model="gpt-4o-2024-05-13",
                temperature=0.5,
            ),
            PARSE_TASK_AGENT_NAME: AgentLLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-sonnet-20241022",
                temperature=0.0,
            ),
            SPEC_WRITER_AGENT_NAME: AgentLLMConfig(
                provider=LLMProvider.OPENAI,
                model="gpt-4-0125-preview",
                temperature=0.0,
            ),
            TASK_BREAKDOWN_AGENT_NAME: AgentLLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-sonnet-20241022",
                temperature=0.5,
            ),
            TECH_LEAD_PLANNING: AgentLLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-sonnet-20240620",
                temperature=0.5,
            ),
            TECH_LEAD_EPIC_BREAKDOWN: AgentLLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-sonnet-20241022",
                temperature=0.5,
            ),
            TROUBLESHOOTER_BUG_REPORT: AgentLLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-sonnet-20240620",
                temperature=0.5,
            ),
            TROUBLESHOOTER_GET_RUN_COMMAND: AgentLLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-sonnet-20240620",
                temperature=0.0,
            ),
        }
    )
    prompt: PromptConfig = PromptConfig()
    log: LogConfig = LogConfig()
    db: DBConfig = DBConfig()
    ui: UIConfig = PlainUIConfig()
    fs: FileSystemConfig = FileSystemConfig()

    def llm_for_agent(self, agent_name: str = "default") -> LLMConfig:
        """
        Fetch an LLM configuration for a given agent.

        If the agent specific configuration doesn't exist, returns the configuration
        for the 'default' agent.
        """

        agent_name = agent_name if agent_name in self.agent else "default"
        agent_config = self.agent[agent_name]
        provider_config = self.llm[agent_config.provider]
        return LLMConfig.from_provider_and_agent_configs(provider_config, agent_config)

    def all_llms(self) -> list[LLMConfig]:
        """
        Get configuration for all defined LLMs.
        """

        return [self.llm_for_agent(agent) for agent in self.agent]


class ConfigLoader:
    """
    Configuration loader takes care of loading and parsing configuration files.

    The default loader is already initialized as `core.config.loader`. To
    load the configuration from a file, use `core.config.loader.load(path)`.

    To get the current configuration, use `core.config.get_config()`.
    """

    config: Config
    config_path: Optional[str]

    def __init__(self):
        self.config_path = None
        self.config = Config()

    @staticmethod
    def _remove_json_comments(json_str: str) -> str:
        """
        Remove comments from a JSON string.

        Removes all lines that start with "//" from the JSON string.

        :param json_str: JSON string with comments.
        :return: JSON string without comments.
        """
        return "\n".join([line for line in json_str.splitlines() if not line.strip().startswith("//")])

    @classmethod
    def from_json(cls: "ConfigLoader", config: str) -> Config:
        """
        Parse JSON Into a Config object.

        :param config: JSON string to parse.
        :return: Config object.
        """
        return Config.model_validate_json(cls._remove_json_comments(config), strict=True)

    def load(self, path: str) -> Config:
        """
        Load a configuration from a file.

        :param path: Path to the configuration file.
        :return: Config object.
        """
        with open(path, "rb") as f:
            raw_config = f.read()

        if b"\x00" in raw_config:
            encoding = "utf-16"
        else:
            encoding = "utf-8"

        text_config = raw_config.decode(encoding)
        self.config = self.from_json(text_config)
        self.config_path = path
        return self.config


loader = ConfigLoader()


def adapt_for_bedrock(config: Config) -> Config:
    """
    Adapt the configuration for use with Bedrock.

    :param config: Configuration to adapt.
    :return: Adapted configuration.
    """
    if "anthropic" not in config.llm:
        return config

    if config.llm["anthropic"].base_url is None or "bedrock/anthropic" not in config.llm["anthropic"].base_url:
        return config

    replacement_map = {
        "claude-3-5-sonnet-20241022": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        "claude-3-5-sonnet-20240620": "us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        "claude-3-sonnet-20240229": "us.anthropic.claude-3-sonnet-20240229-v1:0",
        "claude-3-haiku-20240307": "us.anthropic.claude-3-haiku-20240307-v1:0",
        "claude-3-opus-20240229": "us.anthropic.claude-3-opus-20240229-v1:0",
    }

    for agent in config.agent:
        if config.agent[agent].model in replacement_map:
            config.agent[agent].model = replacement_map[config.agent[agent].model]

    return config


def get_config() -> Config:
    """
    Return current configuration.

    :return: Current configuration object.
    """
    return adapt_for_bedrock(loader.config)


__all__ = ["loader", "get_config"]
