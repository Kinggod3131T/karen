# Karen 1.0 Coding Workflow

Karen 1.0 provides an approval-gated local coding workflow.

## Workflow

1. Karen scans and indexes the selected project.
2. Relevant files are selected as model context.
3. The local coding model creates a structured implementation plan.
4. The plan remains pending until the user approves it.
5. Karen creates a Git checkpoint before modifying files.
6. Approved file operations are executed inside the selected project.
7. Python compilation and automated tests are executed.
8. Karen reviews the resulting Git diff and verification output.
9. The task is marked completed or needs_review.
10. The user reviews and commits the final changes.

Karen does not currently execute unrestricted shell commands, delete arbitrary
files, push code automatically, or modify files outside the configured workspace.
