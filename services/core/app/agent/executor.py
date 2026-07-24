from typing import Any

from services.core.app.schemas import PlannedAction
from services.core.app.security.workspace import resolve_workspace_path
from services.core.app.tools.filesystem import write_text_file


def validate_actions(actions: list[PlannedAction]) -> None:
    """
    Validate every path before executing any operation.

    This prevents an early action from being executed before a later
    invalid path is discovered.
    """

    for action in actions:
        resolve_workspace_path(action.path)


def execute_actions(
    actions: list[PlannedAction],
) -> list[dict[str, Any]]:
    validate_actions(actions)

    results: list[dict[str, Any]] = []

    for action in actions:
        if action.action == "create_directory":
            directory = resolve_workspace_path(action.path)
            already_existed = directory.exists()

            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            results.append(
                {
                    "action": action.action,
                    "path": str(directory),
                    "created": not already_existed,
                    "success": True,
                }
            )

        elif action.action == "write_file":
            if action.content is None:
                raise ValueError(
                    "write_file action is missing content"
                )

            result = write_text_file(
                path=action.path,
                content=action.content,
                confirm=True,
            )

            results.append(
                {
                    "action": action.action,
                    **result,
                    "success": True,
                }
            )

        else:
            raise ValueError(
                f"Unsupported action: {action.action}"
            )

    return results
