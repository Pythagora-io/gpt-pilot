#!/usr/bin/env python3
"""Linear GraphQL API client for common operations."""

import argparse
import glob
import json
import os
import sys
import requests

API_URL = "https://api.linear.app/graphql"

# Default locations for auth-profiles.json (checked in order)
AUTH_PROFILES_PATHS = [
    # Auto-detect agent ID from workspace path, or fall back to glob
    *sorted(glob.glob(os.path.expanduser("~/.openclaw/agents/*/agent/auth-profiles.json"))),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "auth-profiles.json"),
]


def resolve_api_key(explicit_key: str = None) -> str:
    """Resolve the Linear API key from (in priority order):
    1. Explicit --api-key argument
    2. LINEAR_API_KEY environment variable
    3. auth-profiles.json on disk (linear:default profile)
    """
    # 1. Explicit argument
    if explicit_key:
        return explicit_key

    # 2. Environment variable
    env_key = os.environ.get("LINEAR_API_KEY")
    if env_key:
        return env_key

    # 3. Read from auth-profiles.json
    for path in AUTH_PROFILES_PATHS:
        if os.path.isfile(path):
            try:
                with open(path, "r") as f:
                    profiles = json.load(f)
                key = profiles.get("profiles", {}).get("linear:default", {}).get("key")
                if key:
                    return key
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Failed to read {path}: {e}", file=sys.stderr)

    print("Error: No Linear API key found. Provide --api-key, set LINEAR_API_KEY env var, "
          "or ensure auth-profiles.json has a linear:default profile.", file=sys.stderr)
    sys.exit(1)


def gql(api_key: str, query: str, variables: dict = None) -> dict:
    """Execute a GraphQL query against Linear API."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": api_key,
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    resp = requests.post(API_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "errors" in data:
        print(json.dumps({"errors": data["errors"]}, indent=2), file=sys.stderr)
        if not data.get("data"):
            sys.exit(1)

    return data.get("data", {})


# ── Commands ──────────────────────────────────────────────────────────────

def cmd_viewer(args):
    data = gql(args.api_key, """
        query { viewer { id name email admin active } }
    """)
    print(json.dumps(data.get("viewer", {}), indent=2))


def cmd_teams(args):
    data = gql(args.api_key, """
        query { teams { nodes { id name key description } } }
    """)
    print(json.dumps(data.get("teams", {}).get("nodes", []), indent=2))


def cmd_issues(args):
    filters = []
    variables = {}

    if args.team_id:
        filters.append('team: { id: { eq: $teamId } }')
        variables["teamId"] = args.team_id

    if args.state:
        filters.append('state: { name: { eqCaseInsensitive: $stateName } }')
        variables["stateName"] = args.state

    if args.mine:
        filters.append("assignee: { isMe: { eq: true } }")

    filter_str = f"filter: {{ {', '.join(filters)} }}," if filters else ""
    limit = args.limit or 50

    # Build variable declarations
    var_decls = []
    if args.team_id:
        var_decls.append("$teamId: String!")
    if args.state:
        var_decls.append("$stateName: String!")
    var_decl_str = f"({', '.join(var_decls)})" if var_decls else ""

    query = f"""
        query Issues{var_decl_str} {{
            issues({filter_str} first: {limit}, orderBy: updatedAt) {{
                nodes {{
                    id
                    identifier
                    title
                    priority
                    priorityLabel
                    state {{ id name }}
                    assignee {{ id name }}
                    labels {{ nodes {{ id name }} }}
                    createdAt
                    updatedAt
                    url
                }}
            }}
        }}
    """
    data = gql(args.api_key, query, variables if variables else None)
    nodes = data.get("issues", {}).get("nodes", [])
    print(json.dumps(nodes, indent=2))


def cmd_issue(args):
    data = gql(args.api_key, """
        query Issue($id: String!) {
            issue(id: $id) {
                id
                identifier
                title
                description
                priority
                priorityLabel
                estimate
                state { id name }
                assignee { id name }
                creator { id name }
                team { id name key }
                project { id name }
                labels { nodes { id name } }
                comments { nodes { id body user { name } createdAt } }
                createdAt
                updatedAt
                url
            }
        }
    """, {"id": args.id})
    print(json.dumps(data.get("issue", {}), indent=2))


def cmd_create_issue(args):
    input_fields = {
        "teamId": args.team_id,
        "title": args.title,
    }
    if args.description:
        input_fields["description"] = args.description
    if args.priority is not None:
        input_fields["priority"] = args.priority
    if args.state_id:
        input_fields["stateId"] = args.state_id
    if args.assignee_id:
        input_fields["assigneeId"] = args.assignee_id
    if args.label_ids:
        input_fields["labelIds"] = [lid.strip() for lid in args.label_ids.split(",")]
    if args.project_id:
        input_fields["projectId"] = args.project_id

    data = gql(args.api_key, """
        mutation IssueCreate($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    url
                    state { name }
                }
            }
        }
    """, {"input": input_fields})
    result = data.get("issueCreate", {})
    print(json.dumps(result, indent=2))


def cmd_update_issue(args):
    input_fields = {}
    if args.title:
        input_fields["title"] = args.title
    if args.description:
        input_fields["description"] = args.description
    if args.state_id:
        input_fields["stateId"] = args.state_id
    if args.priority is not None:
        input_fields["priority"] = args.priority
    if args.assignee_id:
        input_fields["assigneeId"] = args.assignee_id

    if not input_fields:
        print(json.dumps({"error": "No update fields provided"}), file=sys.stderr)
        sys.exit(1)

    data = gql(args.api_key, """
        mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    state { name }
                    url
                }
            }
        }
    """, {"id": args.id, "input": input_fields})
    result = data.get("issueUpdate", {})
    print(json.dumps(result, indent=2))


def cmd_comment(args):
    data = gql(args.api_key, """
        mutation CommentCreate($input: CommentCreateInput!) {
            commentCreate(input: $input) {
                success
                comment {
                    id
                    body
                    user { name }
                    createdAt
                }
            }
        }
    """, {"input": {"issueId": args.issue_id, "body": args.body}})
    result = data.get("commentCreate", {})
    print(json.dumps(result, indent=2))


def cmd_states(args):
    if args.team_id:
        data = gql(args.api_key, """
            query TeamStates($teamId: String!) {
                team(id: $teamId) {
                    states { nodes { id name type position } }
                }
            }
        """, {"teamId": args.team_id})
        nodes = data.get("team", {}).get("states", {}).get("nodes", [])
    else:
        data = gql(args.api_key, """
            query { workflowStates { nodes { id name type team { id name key } } } }
        """)
        nodes = data.get("workflowStates", {}).get("nodes", [])
    print(json.dumps(nodes, indent=2))


def cmd_labels(args):
    data = gql(args.api_key, """
        query { issueLabels { nodes { id name color } } }
    """)
    print(json.dumps(data.get("issueLabels", {}).get("nodes", []), indent=2))


def cmd_projects(args):
    data = gql(args.api_key, """
        query { projects { nodes { id name state description url } } }
    """)
    print(json.dumps(data.get("projects", {}).get("nodes", []), indent=2))


def cmd_search(args):
    data = gql(args.api_key, """
        query SearchIssues($query: String!) {
            searchIssues(query: $query, first: 25) {
                nodes {
                    id
                    identifier
                    title
                    state { name }
                    assignee { name }
                    url
                }
            }
        }
    """, {"query": args.query})
    nodes = data.get("searchIssues", {}).get("nodes", [])
    print(json.dumps(nodes, indent=2))


def cmd_raw(args):
    data = gql(args.api_key, args.query)
    print(json.dumps(data, indent=2))


# ── CLI ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Linear GraphQL API client")
    parser.add_argument("--api-key", required=False, default=None,
                        help="Linear API key (optional — falls back to LINEAR_API_KEY env var or auth-profiles.json)")
    sub = parser.add_subparsers(dest="command", required=True)

    # viewer
    sub.add_parser("viewer", help="Get authenticated user info")

    # teams
    sub.add_parser("teams", help="List teams")

    # issues
    p = sub.add_parser("issues", help="List issues")
    p.add_argument("--team-id", help="Filter by team ID")
    p.add_argument("--state", help="Filter by state name")
    p.add_argument("--mine", action="store_true", help="Only my assigned issues")
    p.add_argument("--limit", type=int, default=50, help="Max results")

    # issue
    p = sub.add_parser("issue", help="Get a single issue")
    p.add_argument("--id", required=True, help="Issue ID (UUID or shorthand like PAZ-123)")

    # create-issue
    p = sub.add_parser("create-issue", help="Create a new issue")
    p.add_argument("--team-id", required=True, help="Team ID")
    p.add_argument("--title", required=True, help="Issue title")
    p.add_argument("--description", help="Issue description (markdown)")
    p.add_argument("--priority", type=int, help="Priority (0=none, 1=urgent, 2=high, 3=medium, 4=low)")
    p.add_argument("--state-id", help="Workflow state ID")
    p.add_argument("--assignee-id", help="Assignee user ID")
    p.add_argument("--label-ids", help="Comma-separated label IDs")
    p.add_argument("--project-id", help="Project ID")

    # update-issue
    p = sub.add_parser("update-issue", help="Update an issue")
    p.add_argument("--id", required=True, help="Issue ID")
    p.add_argument("--title", help="New title")
    p.add_argument("--description", help="New description")
    p.add_argument("--state-id", help="New state ID")
    p.add_argument("--priority", type=int, help="New priority")
    p.add_argument("--assignee-id", help="New assignee ID")

    # comment
    p = sub.add_parser("comment", help="Add a comment to an issue")
    p.add_argument("--issue-id", required=True, help="Issue ID")
    p.add_argument("--body", required=True, help="Comment body (markdown)")

    # states
    p = sub.add_parser("states", help="List workflow states")
    p.add_argument("--team-id", help="Filter by team (optional)")

    # labels
    sub.add_parser("labels", help="List issue labels")

    # projects
    sub.add_parser("projects", help="List projects")

    # search
    p = sub.add_parser("search", help="Search issues")
    p.add_argument("--query", required=True, help="Search query")

    # raw
    p = sub.add_parser("raw", help="Run a raw GraphQL query")
    p.add_argument("--query", required=True, help="GraphQL query string")

    args = parser.parse_args()

    # Resolve the API key (explicit > env > auth-profiles.json)
    args.api_key = resolve_api_key(args.api_key)

    commands = {
        "viewer": cmd_viewer,
        "teams": cmd_teams,
        "issues": cmd_issues,
        "issue": cmd_issue,
        "create-issue": cmd_create_issue,
        "update-issue": cmd_update_issue,
        "comment": cmd_comment,
        "states": cmd_states,
        "labels": cmd_labels,
        "projects": cmd_projects,
        "search": cmd_search,
        "raw": cmd_raw,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
