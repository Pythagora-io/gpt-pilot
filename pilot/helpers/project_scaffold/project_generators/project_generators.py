import os
import inspect
from dotenv import load_dotenv
from helpers.embeddings import save_embeddings_to_file, load_embeddings_from_file, closest_items
from utils.llm_connection import create_embedding
from .project_generator import generators

from .create_expo_app import CreateExpoApp
from .create_react_app import CreateReactApp
from .create_next_app import CreateNextApp
from .create_vite import CreateVite
from .flutter import Flutter
from .gradle_init import GradleInit
from .spring_init import SpringInit
# Maven archetype?
# TODO: generator for Python projects - best practices (venv/conda/pipenv/poetry?) or cookiecutter?
# TODO: VS Code extension - `npm install -g yo generator-code` and `yo code`

load_dotenv()

EMBEDDING_FILE_NAME = os.path.join(os.path.dirname(__file__), 'generator_embeddings.pkl')


class ProjectGenerators:
    def recommend(self, user_description, embeddings=None):
        if embeddings is None:
            embeddings = load_embeddings_from_file(EMBEDDING_FILE_NAME)

        user_embedding = create_embedding(user_description)

        return closest_items(user_embedding, embeddings, top_n=5)

    def get_embeddings(self):
        if os.path.exists(EMBEDDING_FILE_NAME):
            return load_embeddings_from_file(EMBEDDING_FILE_NAME)

        # module = sys.modules[__name__]
        frame = inspect.currentframe().f_back
        module = inspect.getmodule(frame)

        embeddings = []

        # generators = self._discover_project_generators()

        for generator in generators:
            text = generator.__doc__
            embedding = create_embedding(text)
            embeddings.append({
                "data": {
                    "name": generator.name,
                    "language": generator.language,
                    "topics": generator.topics,
                },
                "embedding": embedding,
            })

        # for name, obj in vars(module).items():
        #     if isinstance(obj, type):
        #         print(name)
        #
        #     if isinstance(obj, type) and hasattr(obj, 'is_project_generator'):
        #         generators.append(obj)
        #         text = obj.__doc__
        #         embedding = create_embedding(text)
        #         embeddings.append({
        #                 "data": {
        #                     "name": obj.name,
        #                     "language": obj.language,
        #                     "topics": obj.topics,
        #                 },
        #                 "embedding": embedding,
        #             })

        # for generator in generators:
        #     print(generator)

        save_embeddings_to_file(embeddings, EMBEDDING_FILE_NAME)
        return embeddings


    # ImportError: attempted relative import with no known parent package
    # def _discover_project_generators(self):
    #     current_directory = os.path.dirname(os.path.abspath(__file__))
    #
    #     for filename in os.listdir(current_directory):
    #         if filename.endswith('.py') and filename != os.path.basename(__file__):  # Exclude the current script
    #             module_name = filename[:-3]  # Strip the .py
    #             module_path = os.path.join(current_directory, filename)
    #
    #             spec = importlib.util.spec_from_file_location(module_name, module_path)
    #             module = importlib.util.module_from_spec(spec)
    #             spec.loader.exec_module(module)
