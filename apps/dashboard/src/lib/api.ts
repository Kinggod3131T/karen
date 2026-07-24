const API_BASE =
  import.meta.env.VITE_KAREN_API ?? "http://127.0.0.1:8080";

export type TaskStatus =
  | "pending"
  | "running"
  | "completed"
  | "needs_review"
  | "rejected"
  | "failed"
  | "committed"
  | "rolled_back";

export interface Health {
  status: string;
  memory: {
    total_gib: number;
    available_gib: number;
    used_percent: number;
  };
  swap: {
    total_gib: number;
    used_gib: number;
    used_percent: number;
  };
  disk?: {
    total_gib: number;
    free_gib: number;
    used_percent: number;
  };
}

export interface PlannedAction {
  action: string;
  path: string;
  content?: string | null;
  reason: string;
}

export interface VerificationResult {
  name: string;
  command: string[];
  return_code: number;
  stdout: string;
  stderr: string;
  passed: boolean;
  timed_out: boolean;
}

export interface ReviewResult {
  verdict: "approved" | "changes_requested";
  summary: string;
  risks: string[];
  suggested_fixes: string[];
}

export interface WorkflowTask {
  id: string;
  project_path: string;
  task: string;
  model: string;
  status: TaskStatus;
  context_files: string[];
  plan: {
    summary: string;
    actions: PlannedAction[];
  };
  checkpoint?: string | null;
  verification_results?: VerificationResult[];
  review?: ReviewResult | null;
  created_at: string;
  updated_at: string;
  error?: string | null;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  const data: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    let message = `Request failed with HTTP ${response.status}`;

    if (
      typeof data === "object" &&
      data !== null &&
      "detail" in data
    ) {
      const detail = (data as { detail: unknown }).detail;

      if (typeof detail === "string") {
        message = detail;
      } else if (
        typeof detail === "object" &&
        detail !== null &&
        "message" in detail
      ) {
        const nestedMessage = (
          detail as { message: unknown }
        ).message;

        if (typeof nestedMessage === "string") {
          message = nestedMessage;
        }
      }
    }

    throw new Error(message);
  }

  return data as T;
}

export function getHealth(): Promise<Health> {
  return request<Health>("/health");
}

export function getTasks(): Promise<WorkflowTask[]> {
  return request<WorkflowTask[]>("/workflow/tasks");
}

export function planSelfUpdate(
  task: string,
): Promise<WorkflowTask> {
  return request<WorkflowTask>("/self-update/plan", {
    method: "POST",
    body: JSON.stringify({
      task,
      model: "qwen2.5-coder:3b",
      max_context_files: 8,
    }),
  });
}

export function approveTask(
  taskId: string,
): Promise<WorkflowTask> {
  return request<WorkflowTask>(
    `/workflow/tasks/${taskId}/approve`,
    {
      method: "POST",
    },
  );
}

export function rejectTask(
  taskId: string,
): Promise<WorkflowTask> {
  return request<WorkflowTask>(
    `/workflow/tasks/${taskId}/reject`,
    {
      method: "POST",
    },
  );
}

export function finalizeSelfUpdate(
  taskId: string,
): Promise<unknown> {
  return request(
    `/self-update/tasks/${taskId}/finalize`,
    {
      method: "POST",
      body: JSON.stringify({
        confirm: true,
      }),
    },
  );
}
