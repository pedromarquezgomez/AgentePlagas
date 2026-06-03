from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"


def _python_files(path: Path) -> list[Path]:
    return [
        file_path
        for file_path in path.rglob("*.py")
        if "__pycache__" not in file_path.parts
    ]


def _relative(path: Path) -> str:
    return path.relative_to(BACKEND_ROOT).as_posix()


def test_tool_execution_service_is_only_called_from_policy_protected_route() -> None:
    call_sites = []
    for file_path in _python_files(APP_ROOT):
        text = file_path.read_text()
        if ".execute_execution_record(" in text:
            call_sites.append(_relative(file_path))

    assert call_sites == ["app/routes/tools.py"]


def test_policy_engine_is_evaluated_before_tool_execution() -> None:
    route_text = (APP_ROOT / "routes" / "tools.py").read_text()

    policy_index = route_text.index("policy_engine.evaluate(")
    execution_index = route_text.index(".execute_execution_record(")

    assert policy_index < execution_index


def test_runtime_providers_do_not_import_or_execute_backend_tools() -> None:
    providers_root = APP_ROOT / "harness" / "providers"
    blocked_fragments = [
        "ToolExecutionService",
        "IncidentService",
        "FirestoreService",
        "get_firestore_service",
        "GmailToolExecutor",
        ".execute_execution_record(",
        ".create_draft(",
        ".send_email(",
    ]

    for file_path in _python_files(providers_root):
        text = file_path.read_text()
        for fragment in blocked_fragments:
            assert fragment not in text, f"{fragment} found in {_relative(file_path)}"


def test_skills_are_metadata_not_execution_layers() -> None:
    skills_root = APP_ROOT / "skills"
    blocked_fragments = [
        "from app.services",
        "from app.tools",
        "FirestoreService",
        "ToolExecutionService",
        "GmailToolExecutor",
        "create_document(",
        "update_document(",
        ".execute_execution_record(",
    ]

    for file_path in _python_files(skills_root):
        text = file_path.read_text()
        for fragment in blocked_fragments:
            assert fragment not in text, f"{fragment} found in {_relative(file_path)}"


def test_tool_registry_contains_metadata_only() -> None:
    tools_root = APP_ROOT / "tools"
    blocked_fragments = [
        "from app.services",
        "FirestoreService",
        "ToolExecutionService",
        "GmailToolExecutor",
        "create_document(",
        "update_document(",
        ".create_draft(",
        ".send_email(",
        ".execute_execution_record(",
    ]

    for file_path in _python_files(tools_root):
        text = file_path.read_text()
        for fragment in blocked_fragments:
            assert fragment not in text, f"{fragment} found in {_relative(file_path)}"
