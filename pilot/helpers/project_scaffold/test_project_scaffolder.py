import os
import pytest
from dotenv import load_dotenv
from unittest.mock import patch, Mock
from helpers.AgentConvo import AgentConvo
from helpers.Project import Project
from helpers.agents.Architect import Architect
from test.mock_terminal_size import mock_terminal_size
from .project_scaffolder import ProjectScaffolder

load_dotenv()
project_scaffolder = ProjectScaffolder()


@pytest.mark.uses_tokens
class TestProjectScaffolder:
    def setup_method(self):
        name = 'Scaffolder Test Project'
        self.project = Project({
                'app_id': 'test-scaffolder',
                'name': name,
                'app_type': ''
            },
            name=name,
            description='A web-based chat app.',
            architecture=[],
            user_stories=[],
            current_step='coding',
        )

        self.project.root_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                              '../../../workspace/test-scaffolder'))
        self.project.technologies = []
        self.project.app = None
        self.architect = Architect(self.project)

    @patch('os.get_terminal_size', mock_terminal_size)
    @patch('helpers.AgentConvo.get_development_step_from_hash_id')
    def test_select_project_generator(self, mock_get_saved_step):
        # Given
        convo = AgentConvo(self.architect)

        # When
        generator = project_scaffolder.select_project_generator(self.project, convo)

        # Then prompt should include relevant generators
        assert "[{'name': 'create-react-app', 'language': 'JavaScript, TypeScript', 'topics': ['react', 'javascript', 'typescript']}, " \
                "{'name': 'flutter', 'language': 'Dart, Kotlin, Swift', 'topics': ['Flutter', 'mobile', 'dart', 'kotlin', 'swift']}, " \
            "{'name': 'create-next-app', 'language': 'JavaScript, TypeScript', 'topics': ['Next.js', 'javascript', 'typescript']}, " \
            "{'name': 'create vite', 'language': 'JavaScript, TypeScript', " \
               "'topics': ['vite', 'javascript', 'typescript', 'vanilla javascript', 'vue', 'react', 'preact', 'lit', 'svelte', 'solid-js']}, " \
            "{'name': 'spring init', 'language': 'Java, Kotlin', 'topics': ['Spring', 'Java', 'Kotlin']}]" \
            in convo.messages[1]['content']

        # And prompt should include relevant template repos
        assert "[{'repo': 'vercel-labs/ai-chatbot', " \
                    "'description': 'A full-featured, hackable Next.js AI chatbot built by Vercel Labs', " \
                    "'stars': 2922, 'language': 'TypeScript', " \
                    "'topics': ['ai', 'chatgpt', 'gpt-3', 'gpt-4', 'nextjs', 'react', 'redis', 'shadcn-ui', 'vercel']}, " \
               "{'repo': 'wechaty/getting-started', 'description': 'A Starter Project Template for Wechaty works out-of-the-box', " \
                    "'stars': 673, 'language': 'JavaScript', 'topics': ['bot', 'chatbot', 'getting-started', 'video-tutorial', 'wechat', 'wechaty']}, " \
               "{'repo': 'rizwansoaib/whatsapp-monitor', 'description': 'Free Whatsapp Online Tracker  📲  | WhatsApp last seen tracker | [Get Notification 🔔  and history 📜 of Online WhatsApp Contact]', " \
                    "'stars': 655, 'language': 'JavaScript', " \
                    "'topics': ['android-notification-service', 'android-whatsapp-monitor', 'android-whatsapp-tracker', 'browser-extension', 'chrome-extensions', 'free', 'free-online-tracker', 'free-whatsapp-online-tracker', 'online-status', 'online-tracker', 'smartphone-notification', 'tracker-online', 'whatsapp-contacts', 'whatsapp-desktop', 'whatsapp-desktop-client', 'whatsapp-monitor', 'whatsapp-notification', 'whatsapp-online', 'whatsapp-tracker', 'whatsapp-web-linux']}, " \
               "{'repo': 'codebuddies/codebuddies', 'description': 'CodeBuddies.org: Community-organized hangouts for learning programming together - community-built using MeteorJS', " \
                    "'stars': 524, 'language': 'JavaScript', 'topics': ['google', 'groups', 'hangouts', 'jitsi', 'learning', 'peer-to-peer', 'schedule-hangouts', 'slack', 'study', 'volunteers']}, " \
               "{'repo': 'vihangayt0/Astro-MD', 'description': 'World Best Multi-device Whatsapp Bot. Created by Vihanga-YT', 'stars': 225, 'language': 'JavaScript', 'topics': []}]" \
            in convo.messages[1]['content']

        if len(generator) == 3:
            # Generator with options
            name, reason, options = generator
            assert name == 'create-react-app'
        else:
            # Template repository
            name, reason = generator
            assert name == 'wechaty/getting-started'

        assert reason is not None


    @patch('os.get_terminal_size', mock_terminal_size)
    @patch('helpers.AgentConvo.get_development_step_from_hash_id')
    def test_select_project_generator_typescript(self, mock_get_saved_step):
        # Given
        convo = AgentConvo(self.architect)
        self.project.description = 'A web-based chat app in TypeScript.'

        # When
        generator = project_scaffolder.select_project_generator(self.project, convo)

        # Then prompt should include relevant generators
        assert "[{'name': 'create-next-app', 'language': 'JavaScript, TypeScript', 'topics': ['Next.js', 'javascript', 'typescript']}, " \
               "{'name': 'create-react-app', 'language': 'JavaScript, TypeScript', 'topics': ['react', 'javascript', 'typescript']}, " \
               "{'name': 'create vite', 'language': 'JavaScript, TypeScript', 'topics': ['vite', 'javascript', 'typescript', 'vanilla javascript', 'vue', 'react', 'preact', 'lit', 'svelte', 'solid-js']}, " \
               "{'name': 'flutter', 'language': 'Dart, Kotlin, Swift', 'topics': ['Flutter', 'mobile', 'dart', 'kotlin', 'swift']}, " \
               "{'name': 'spring init', 'language': 'Java, Kotlin', 'topics': ['Spring', 'Java', 'Kotlin']}]" \
            in convo.messages[1]['content']

        # And prompt should include relevant template repos
        assert "[{'repo': 'vercel-labs/ai-chatbot', 'description': 'A full-featured, hackable Next.js AI chatbot built by Vercel Labs', " \
                "'stars': 2922, 'language': 'TypeScript', " \
                "'topics': ['ai', 'chatgpt', 'gpt-3', 'gpt-4', 'nextjs', 'react', 'redis', 'shadcn-ui', 'vercel']}, " \
               "{'repo': 'electron/electron-quick-start-typescript', 'description': 'Clone to try a simple Electron app (in TypeScript)', " \
                "'stars': 1128, 'language': 'TypeScript', 'topics': []}, " \
               "{'repo': 'zhengbangbo/chat-simplifier', 'description': 'Simplify your chat content in seconds (by OpenAI)', " \
                "'stars': 529, 'language': 'TypeScript', 'topics': ['openai']}, " \
               "{'repo': 'shanhuiyang/TypeScript-MERN-Starter', 'description': 'Build a real fullstack app (backend+website+mobile) in 100% Typescript', " \
                "'stars': 327, 'language': 'TypeScript', 'topics': ['android', 'expo', 'express', 'fullstack', 'ios', 'javascript', 'mern', 'mongodb', 'native-base', 'node', 'nodejs', 'oauth2-server', 'react', 'react-native', 'react-redux', 'react-router-v4', 'semantic-ui', 'template', 'typescript', 'webapp']}, " \
               "{'repo': 'nextauthjs/next-auth-typescript-example', 'description': 'An example project that shows how to use NextAuth with TypeScript', " \
                "'stars': 211, 'language': 'TypeScript', 'topics': ['nextauth', 'typescript', 'vercel']}]" \
            in convo.messages[1]['content']

        # "{'repo': 'blinks32/Taxi-booking-uber-clone-with-ionic-6-capacitor-4', 'description': 'This is a complete ride booking app, It uses google maps cordova plugin, firebase database and onesignal as notification provider.', " \
        #  "'stars': 298, 'language': 'TypeScript', 'topics': ['android', 'angular4', 'capacitor', 'cordova', 'firebase', 'google-maps-android', 'ionic3', 'ionic5', 'ios', 'nexmo-api', 'nodejs', 'onesignal', 'paystack', 'scss', 'stripe-api', 'typescript']}]" \

        if len(generator) == 3:
            # Generator with options
            name, reason, options = generator
            assert name == 'create-next-app'
            # create-next-app --typescript (or --ts)
            # create-next-app --example with-tailwindcss
            # create-next-app --example with-typescript
        else:
            # Template repository
            name, reason = generator
            assert name == 'shanhuiyang/TypeScript-MERN-Starter'

        assert reason is not None

    @patch('os.get_terminal_size', mock_terminal_size)
    @patch('helpers.AgentConvo.get_development_step_from_hash_id')
    def test_select_project_generator_mobile(self, mock_get_saved_step):
        # Given
        convo = AgentConvo(self.architect)
        self.project.description = 'A mobile app which allows users to chat'

        # When
        generator = project_scaffolder.select_project_generator(self.project, convo)

        # Then prompt should include relevant generators
        assert "[{'name': 'flutter', 'language': 'Dart, Kotlin, Swift', 'topics': ['Flutter', 'mobile', 'dart', 'kotlin', 'swift']}, " \
               "{'name': 'create-react-app', 'language': 'JavaScript, TypeScript', 'topics': ['react', 'javascript', 'typescript']}, " \
               "{'name': 'create-expo-app', 'language': 'JavaScript, TypeScript', 'topics': ['react native', 'javascript', 'typescript', 'mobile', 'expo']}, " \
               "{'name': 'spring init', 'language': 'Java, Kotlin', 'topics': ['Spring', 'Java', 'Kotlin']}, " \
               "{'name': 'create-next-app', 'language': 'JavaScript, TypeScript', 'topics': ['Next.js', 'javascript', 'typescript']}]" \
            in convo.messages[1]['content']

        # And prompt should include relevant template repos
        assert "{'repo': 'Kashif-E/KMMNewsAPP', 'description': 'Kotlin multi platform project template and sample app with everything shared except the UI. Built with clean architecture + MVI', " \
               "'stars': 260, 'language': 'Kotlin', 'topics': ['android', 'androidarchitecturecomponets', 'coroutines', 'ios', 'jetpack-compose', 'kmm', 'koin', 'koin-kotlin', 'kotlin', 'kotlin-android', 'kotlin-multiplatform', 'kotlin-multiplatform-mobile', 'ktor-client', 'mvi-clean-architecture', 'mvi-coroutines-flow', 'swift', 'swiftui']}, " \
               "{'repo': 'vihangayt0/Astro-MD', 'description': 'World Best Multi-device Whatsapp Bot. Created by Vihanga-YT', 'stars': 225, 'language': 'JavaScript', 'topics': []}" \
            in convo.messages[1]['content']

        if len(generator) == 3:
            # Generator with options
            name, reason, options = generator
            assert name == 'create-expo-app'
            # --template=expo-template-blank
        else:
            # Template repository
            name, reason = generator
            assert name is not None

        assert reason is not None
