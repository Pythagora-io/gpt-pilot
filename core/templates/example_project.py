from core.db.models import Complexity

EXAMPLE_PROJECT_DESCRIPTION = """
The application is a simple ToDo app built using React. Its primary function is to allow users to manage a list of tasks (todos). Each task has a description and a state (open or completed, with the default state being open). The application is frontend-only, with no user sign-up or authentication process. The goal is to provide a straightforward and user-friendly interface for task management.

Features:
1. Display of Todos: A list that displays all todo items. Each item shows its description and a checkbox to indicate its state (open or completed).
2. Add New Todo: A button to add a new todo item. Clicking this button will prompt the user to enter a description for the new todo.
3. Toggle State: Each todo item includes a checkbox. Checking/unchecking this box toggles the todo's state between open and completed.
4. Local Storage: The application will use the browser's local storage to persist todos between sessions, ensuring that users do not lose their data upon reloading the application.

Functional Specification:
- Upon loading the application, it fetches existing todos from the local storage and displays them in a list.
- Each todo item in the list displays a checkbox and a description. The checkbox reflects the todo's current state (checked for completed, unchecked for open).
- When the user checks or unchecks a checkbox, the application updates the state of the corresponding todo item and saves the updated list to local storage.
- Clicking the "Add New Todo" button prompts the user to enter a description for the new todo. Upon confirmation, the application adds the new todo (with the default state of open) to the list and updates local storage.
- The application does not support deleting or editing todo items to keep the interface and interactions simple.
- Todos persist between sessions using the browser's local storage. The application saves any changes to the todo list (additions or state changes) in local storage and retrieves this data when the application is reloaded.

Technical Specification:
- Platform/Technologies: The application is a web application developed using React on frontend and Express on the backend, using SQLite as the database.
- Styling: Use Bootstrap 5 for a simple and functional interface. Load Boostrap from the CDN (don't install it locally):
    - https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css
    - https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/js/bootstrap.bundle.min.js
- State Management: Directly in the React component
    - make sure to initialize the state from the local storage as default (... = useState(JSON.parse(localStorage.getItem('todos')) || []) to avoid race conditions
- Data Persistence: Using the SQLite database on the backend via a REST API.
"""

EXAMPLE_PROJECT_ARCHITECTURE = {
    "architecture": (
        "The application is a client-side React web application that uses local storage for data persistence. "
        "It consists of a single page with components for listing todos, adding new todos, and toggling their completion status. "
        "State management is handled directly within React components, leveraging useState and useEffect hooks for state manipulation and side effects, respectively. "
        "Bootstrap 5 is used for styling to provide a responsive and accessible UI."
    ),
    "system_dependencies": [
        {
            "name": "Node.js",
            "description": "JavaScript runtime needed to run the React development tools and build the project.",
            "test": "node --version",
            "required_locally": True,
        }
    ],
    "package_dependencies": [
        {"name": "react", "description": "A JavaScript library for building user interfaces."},
        {"name": "react-dom", "description": "Serves as the entry point to the DOM and server renderers for React."},
        {"name": "bootstrap", "description": "Frontend framework for developing responsive and mobile-first websites."},
    ],
    "templates": {
        "javascript_react": {},
    },
}

EXAMPLE_PROJECT_PLAN = [
    {
        "description": (
            "Create a new component TodoList: This component will display the list of todo items. "
            "Use localStorage directly to access the current state of todos and map over them, rendering each todo item as a list item. "
            "Each item should display the todo's description and a checkbox that reflects the todo's state (checked for completed, unchecked for open). "
            "When the checkbox is clicked, dispatch an action to toggle the state of the todo. "
            "Also create AddTodo: This component will include a button that, when clicked, displays a prompt asking the user for a description of the new todo. "
            "Upon confirmation, dispatch an action to add the new todo to the state with a default state of open. "
            "Ensure the component also updates the local storage with the new list of todos. "
            "Finally, use TodoList and AddTodo components in App component to implement the required functionality. "
            "Integrate Boostrap 5 for styling - add CSS/JS to index.html, style App.jsx and other files as appropriate."
        ),
        "status": "todo",
        "sub_epic_id": 1,
    }
]


EXAMPLE_PROJECTS = {
    "example-project": {
        "description": EXAMPLE_PROJECT_DESCRIPTION,
        "architecture": EXAMPLE_PROJECT_ARCHITECTURE,
        "complexity": Complexity.SIMPLE,
        "plan": EXAMPLE_PROJECT_PLAN,
    }
}

DEFAULT_EXAMPLE_PROJECT = "example-project"
