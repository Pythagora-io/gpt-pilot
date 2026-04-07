#!/usr/bin/env python3
"""
Test infrastructure connections during onboarding.
Usage:
    python3 test_connections.py mongodb <connection_string>
    python3 test_connections.py redis <host> <port> [password]
    python3 test_connections.py postgres <host> <port> <database> <user> <password>
    python3 test_connections.py mysql <host> <port> <database> <user> <password>
    python3 test_connections.py github <token> [org_or_user]
    python3 test_connections.py ssh <host> <user> <key_path>
    python3 test_connections.py http <url> [expected_status]
"""

import sys
import json
import subprocess
import os


def test_mongodb(connection_string):
    """Test MongoDB connection and check permissions."""
    try:
        from pymongo import MongoClient
        client = MongoClient(connection_string, serverSelectionTimeoutMS=10000)
        # Test connection
        server_info = client.server_info()
        db_names = client.list_database_names()

        # Check if read-only by attempting a write to a test collection
        test_db = client["__devops_permission_test"]
        is_readonly = False
        try:
            test_db["__test"].insert_one({"test": True})
            # If write succeeded, clean up and warn
            test_db["__test"].delete_many({})
            client.drop_database("__devops_permission_test")
            is_readonly = False
        except Exception:
            is_readonly = True

        client.close()

        result = {
            "status": "connected",
            "version": server_info.get("version", "unknown"),
            "databases": db_names,
            "database_count": len(db_names),
            "read_only": is_readonly,
        }

        if not is_readonly:
            result["warning"] = "⚠️ This connection has WRITE access. Please provide a read-only user."

        print(json.dumps(result, indent=2))
        return 0 if is_readonly else 1

    except ImportError:
        print(json.dumps({"status": "error", "message": "pymongo not installed. Run: pip install pymongo"}))
        return 2
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        return 2


def test_redis(host, port, password=None):
    """Test Redis connection and check permissions."""
    try:
        import redis as redis_lib
        r = redis_lib.Redis(host=host, port=int(port), password=password, decode_responses=True, socket_timeout=10)
        info = r.info("server")

        # Check ACL permissions
        is_restricted = False
        try:
            # Try a write command
            r.set("__devops_permission_test", "test")
            r.delete("__devops_permission_test")
            is_restricted = False
        except redis_lib.exceptions.ResponseError as e:
            if "NOPERM" in str(e) or "no permission" in str(e).lower():
                is_restricted = True
            else:
                raise

        db_size = r.dbsize()
        r.close()

        result = {
            "status": "connected",
            "version": info.get("redis_version", "unknown"),
            "db_size": db_size,
            "read_only": is_restricted,
        }

        if not is_restricted:
            result["warning"] = (
                "⚠️ This connection has WRITE access. If your Redis provider supports ACLs, "
                "please create a read-only user. If not, the agent will self-restrict to read commands only."
            )

        print(json.dumps(result, indent=2))
        return 0

    except ImportError:
        print(json.dumps({"status": "error", "message": "redis not installed. Run: pip install redis"}))
        return 2
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        return 2


def test_postgres(host, port, database, user, password):
    """Test PostgreSQL connection and check permissions."""
    try:
        import psycopg2
        conn = psycopg2.connect(host=host, port=int(port), dbname=database, user=user, password=password, connect_timeout=10)
        cur = conn.cursor()

        # Get version
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]

        # List tables
        cur.execute("SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema');")
        tables = cur.fetchall()

        # Check write permissions
        is_readonly = False
        try:
            cur.execute("CREATE TEMP TABLE __devops_test (id int);")
            cur.execute("DROP TABLE __devops_test;")
            conn.rollback()
            is_readonly = False
        except Exception:
            conn.rollback()
            is_readonly = True

        conn.close()

        result = {
            "status": "connected",
            "version": version.split(",")[0] if version else "unknown",
            "table_count": len(tables),
            "schemas": list(set(t[0] for t in tables)),
            "read_only": is_readonly,
        }

        if not is_readonly:
            result["warning"] = "⚠️ This user has WRITE access. Please provide a user with SELECT-only grants."

        print(json.dumps(result, indent=2))
        return 0 if is_readonly else 1

    except ImportError:
        print(json.dumps({"status": "error", "message": "psycopg2 not installed. Run: pip install psycopg2-binary"}))
        return 2
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        return 2


def test_mysql(host, port, database, user, password):
    """Test MySQL connection and check permissions."""
    try:
        import mysql.connector
        conn = mysql.connector.connect(host=host, port=int(port), database=database, user=user, password=password, connection_timeout=10)
        cur = conn.cursor()

        # Get version
        cur.execute("SELECT VERSION();")
        version = cur.fetchone()[0]

        # List tables
        cur.execute("SHOW TABLES;")
        tables = cur.fetchall()

        # Check grants
        cur.execute(f"SHOW GRANTS FOR CURRENT_USER();")
        grants = [row[0] for row in cur.fetchall()]

        has_write = any(
            perm in grant.upper()
            for grant in grants
            for perm in ["INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "ALL PRIVILEGES"]
        )

        conn.close()

        result = {
            "status": "connected",
            "version": version,
            "table_count": len(tables),
            "read_only": not has_write,
            "grants": grants,
        }

        if has_write:
            result["warning"] = "⚠️ This user has WRITE access. Please provide a user with SELECT-only grants."

        print(json.dumps(result, indent=2))
        return 0 if not has_write else 1

    except ImportError:
        print(json.dumps({"status": "error", "message": "mysql-connector not installed. Run: pip install mysql-connector-python"}))
        return 2
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        return 2


def test_github(token, org_or_user=None):
    """Test GitHub PAT and check scopes."""
    import urllib.request
    import urllib.error

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        # Check token validity and scopes
        req = urllib.request.Request("https://api.github.com/user", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            user_data = json.loads(resp.read())
            scopes = resp.headers.get("X-OAuth-Scopes", "")

        # Check for write scopes
        write_scopes = ["repo", "admin", "write", "delete", "workflow", "packages"]
        has_write = any(ws in scopes.lower() for ws in write_scopes) if scopes else False

        # For fine-grained PATs, scopes header may be empty — that's OK (permissions are set per-repo)

        # List repos
        url = f"https://api.github.com/orgs/{org_or_user}/repos?per_page=5" if org_or_user else "https://api.github.com/user/repos?per_page=5&sort=updated"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            repos = json.loads(resp.read())

        result = {
            "status": "connected",
            "user": user_data.get("login", "unknown"),
            "scopes": scopes if scopes else "(fine-grained PAT — no classic scopes)",
            "sample_repos": [r["full_name"] for r in repos[:5]],
            "read_only": not has_write,
        }

        if has_write:
            result["warning"] = (
                "⚠️ This token has WRITE scopes. Please create a fine-grained PAT with "
                "only 'Contents: read' and 'Metadata: read' permissions."
            )

        print(json.dumps(result, indent=2))
        return 0 if not has_write else 1

    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(json.dumps({"status": "error", "message": "Invalid token — authentication failed"}))
        elif e.code == 403:
            print(json.dumps({"status": "error", "message": "Token valid but access forbidden — check permissions"}))
        else:
            print(json.dumps({"status": "error", "message": f"HTTP {e.code}: {e.reason}"}))
        return 2
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        return 2


def test_ssh(host, user, key_path):
    """Test SSH connection."""
    try:
        result = subprocess.run(
            ["ssh", "-i", key_path, "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10",
             f"{user}@{host}", "whoami && hostname && uname -a"],
            capture_output=True, text=True, timeout=15
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            print(json.dumps({
                "status": "connected",
                "user": lines[0] if len(lines) > 0 else "unknown",
                "hostname": lines[1] if len(lines) > 1 else "unknown",
                "system": lines[2] if len(lines) > 2 else "unknown",
            }, indent=2))
            return 0
        else:
            print(json.dumps({"status": "error", "message": result.stderr.strip()}))
            return 2

    except subprocess.TimeoutExpired:
        print(json.dumps({"status": "error", "message": "SSH connection timed out"}))
        return 2
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        return 2


def test_http(url, expected_status=200):
    """Test an HTTP endpoint."""
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            body = resp.read(500).decode("utf-8", errors="replace")

        result = {
            "status": "connected" if status == int(expected_status) else "unexpected_status",
            "http_status": status,
            "body_preview": body[:200],
        }
        print(json.dumps(result, indent=2))
        return 0 if status == int(expected_status) else 1

    except urllib.error.HTTPError as e:
        print(json.dumps({"status": "error", "http_status": e.code, "message": e.reason}))
        return 2
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        return 2


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    handlers = {
        "mongodb": lambda: test_mongodb(args[0]) if len(args) >= 1 else print("Usage: test_connections.py mongodb <connection_string>"),
        "redis": lambda: test_redis(args[0], args[1], args[2] if len(args) > 2 else None) if len(args) >= 2 else print("Usage: test_connections.py redis <host> <port> [password]"),
        "postgres": lambda: test_postgres(*args[:5]) if len(args) >= 5 else print("Usage: test_connections.py postgres <host> <port> <db> <user> <password>"),
        "mysql": lambda: test_mysql(*args[:5]) if len(args) >= 5 else print("Usage: test_connections.py mysql <host> <port> <db> <user> <password>"),
        "github": lambda: test_github(args[0], args[1] if len(args) > 1 else None) if len(args) >= 1 else print("Usage: test_connections.py github <token> [org]"),
        "ssh": lambda: test_ssh(*args[:3]) if len(args) >= 3 else print("Usage: test_connections.py ssh <host> <user> <key_path>"),
        "http": lambda: test_http(args[0], args[1] if len(args) > 1 else 200) if len(args) >= 1 else print("Usage: test_connections.py http <url> [expected_status]"),
    }

    if cmd in handlers:
        return handlers[cmd]()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
