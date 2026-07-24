import {
  Activity,
  BrainCircuit,
  CheckCircle2,
  Code2,
  Cpu,
  Database,
  FileCode2,
  GitCommit,
  HardDrive,
  KeyRound,
  LoaderCircle,
  MemoryStick,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  XCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";

import {
  approveTask,
  finalizeSelfUpdate,
  getHealth,
  getTasks,
  planSelfUpdate,
  rejectTask,
} from "./lib/api";
import type {
  Health,
  TaskStatus,
  WorkflowTask,
} from "./lib/api";

type PageId =
  | "overview"
  | "self-update"
  | "coding-tasks"
  | "tools"
  | "memory"
  | "security";

interface NavigationItem {
  id: PageId;
  label: string;
  icon: LucideIcon;
}

const navigationItems: NavigationItem[] = [
  {
    id: "overview",
    label: "Overview",
    icon: Activity,
  },
  {
    id: "self-update",
    label: "Self Update",
    icon: Sparkles,
  },
  {
    id: "coding-tasks",
    label: "Coding Tasks",
    icon: Code2,
  },
  {
    id: "tools",
    label: "Tools",
    icon: TerminalSquare,
  },
  {
    id: "memory",
    label: "Memory",
    icon: Database,
  },
  {
    id: "security",
    label: "Security",
    icon: ShieldCheck,
  },
];

const pageCopy: Record<
  PageId,
  {
    eyebrow: string;
    title: string;
    description: string;
  }
> = {
  overview: {
    eyebrow: "Local AI Engineering System",
    title: "Karen Control Center",
    description:
      "Monitor resources, review activity and control Karen's local engineering workflows.",
  },
  "self-update": {
    eyebrow: "Controlled Evolution",
    title: "Self Update",
    description:
      "Plan changes to Karen's own source code, inspect them and approve execution safely.",
  },
  "coding-tasks": {
    eyebrow: "Approval-Gated Automation",
    title: "Coding Tasks",
    description:
      "Review every generated implementation plan, verification result and AI assessment.",
  },
  tools: {
    eyebrow: "Restricted Workstation Access",
    title: "Tools",
    description:
      "Inspect the safe terminal, Git, Docker and repository capabilities available to Karen.",
  },
  memory: {
    eyebrow: "Project Intelligence",
    title: "Memory",
    description:
      "Inspect the project files and context records Karen has used for engineering tasks.",
  },
  security: {
    eyebrow: "Safety Kernel",
    title: "Security",
    description:
      "Review workspace isolation, approval requirements and protected operations.",
  },
};

function statusClasses(status: TaskStatus): string {
  switch (status) {
    case "completed":
    case "committed":
      return "border-emerald-400/30 bg-emerald-400/10 text-emerald-300";

    case "running":
      return "border-sky-400/30 bg-sky-400/10 text-sky-300";

    case "needs_review":
      return "border-amber-400/30 bg-amber-400/10 text-amber-300";

    case "failed":
    case "rejected":
      return "border-red-400/30 bg-red-400/10 text-red-300";

    case "rolled_back":
      return "border-violet-400/30 bg-violet-400/10 text-violet-300";

    default:
      return "border-zinc-400/20 bg-zinc-400/10 text-zinc-300";
  }
}

function formatStatus(status: TaskStatus): string {
  return status.replaceAll("_", " ");
}

interface MetricCardProps {
  label: string;
  value: string;
  detail: string;
  icon: ReactNode;
}

function MetricCard({
  label,
  value,
  detail,
  icon,
}: MetricCardProps) {
  return (
    <article className="glass-panel rounded-2xl p-5">
      <div className="mb-5 flex items-center justify-between">
        <span className="text-sm text-zinc-400">
          {label}
        </span>

        <span className="text-red-300">
          {icon}
        </span>
      </div>

      <div className="text-2xl font-semibold tracking-tight">
        {value}
      </div>

      <div className="mt-1 text-xs text-zinc-500">
        {detail}
      </div>
    </article>
  );
}

interface TaskCardProps {
  task: WorkflowTask;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
  onFinalize: () => void;
}

function TaskCard({
  task,
  busy,
  onApprove,
  onReject,
  onFinalize,
}: TaskCardProps) {
  const canFinalize =
    task.task_kind === "self_update" &&
    task.status === "completed";

  return (
    <article className="rounded-2xl border border-white/8 bg-black/20 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="task-title text-sm font-medium leading-5">
            {task.task}
          </div>

          <div className="mt-1 text-xs text-zinc-600">
            {task.model} · {task.id.slice(0, 8)}
          </div>
        </div>

        <span
          className={[
            "rounded-full border px-2.5 py-1",
            "text-[11px] font-medium capitalize",
            statusClasses(task.status),
          ].join(" ")}
        >
          {formatStatus(task.status)}
        </span>
      </div>

      <p className="mt-4 text-xs leading-5 text-zinc-400">
        {task.plan.summary}
      </p>

      <div className="mt-3 space-y-1.5">
        {task.plan.actions.slice(0, 4).map((action, index) => (
          <div
            key={`${action.action}-${action.path}-${index}`}
            className="truncate rounded-lg bg-white/[0.035] px-3 py-2 font-mono text-[11px] text-zinc-400"
            title={action.path}
          >
            <span className="text-red-300">
              {action.action}
            </span>
            {": "}
            {action.path}
          </div>
        ))}
      </div>

      {task.review && (
        <div className="mt-3 rounded-xl border border-white/7 bg-black/20 p-3">
          <div className="text-xs font-medium text-zinc-300">
            Review: {task.review.verdict}
          </div>

          <p className="mt-1 text-xs leading-5 text-zinc-500">
            {task.review.summary}
          </p>
        </div>
      )}

      {task.error && (
        <div className="mt-3 rounded-xl border border-red-400/20 bg-red-500/8 p-3 text-xs text-red-300">
          {task.error}
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {task.status === "pending" && (
          <>
            <button
              type="button"
              onClick={onApprove}
              disabled={busy}
              className="flex items-center gap-1.5 rounded-lg bg-emerald-500/15 px-3 py-2 text-xs text-emerald-300 transition hover:bg-emerald-500/25 disabled:opacity-50"
            >
              <Play size={14} />
              Approve
            </button>

            <button
              type="button"
              onClick={onReject}
              disabled={busy}
              className="flex items-center gap-1.5 rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-300 transition hover:bg-red-500/20 disabled:opacity-50"
            >
              <XCircle size={14} />
              Reject
            </button>
          </>
        )}

        {canFinalize && (
          <button
            type="button"
            onClick={onFinalize}
            disabled={busy}
            className="flex items-center gap-1.5 rounded-lg bg-red-500/15 px-3 py-2 text-xs text-red-200 transition hover:bg-red-500/25 disabled:opacity-50"
          >
            <GitCommit size={14} />
            Finalize commit
          </button>
        )}

        {task.status === "completed" && (
          <span className="flex items-center gap-1.5 px-2 py-2 text-xs text-emerald-400">
            <CheckCircle2 size={14} />
            Verification passed
          </span>
        )}

        {task.status === "committed" && (
          <span className="flex items-center gap-1.5 px-2 py-2 text-xs text-emerald-400">
            <GitCommit size={14} />
            Commit created
          </span>
        )}

        {busy && (
          <LoaderCircle
            className="animate-spin text-zinc-400"
            size={17}
          />
        )}
      </div>
    </article>
  );
}

function App() {
  const [activePage, setActivePage] =
    useState<PageId>("overview");
  const [health, setHealth] = useState<Health | null>(null);
  const [tasks, setTasks] = useState<WorkflowTask[]>([]);
  const [prompt, setPrompt] = useState(
    "Improve Karen's dashboard while preserving the existing API.",
  );
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pendingTasks = useMemo(
    () =>
      tasks.filter((task) => task.status === "pending").length,
    [tasks],
  );

  const selfUpdateTasks = useMemo(
    () =>
      tasks.filter(
        (task) => task.task_kind === "self_update",
      ),
    [tasks],
  );

  const contextFiles = useMemo(() => {
    const files = new Set<string>();

    for (const task of tasks) {
      for (const file of task.context_files) {
        files.add(file);
      }
    }

    return [...files].sort();
  }, [tasks]);

  const refresh = useCallback(async () => {
    try {
      const [healthData, taskData] = await Promise.all([
        getHealth(),
        getTasks(),
      ]);

      setHealth(healthData);
      setTasks(taskData);
      setError(null);
    } catch (caught) {
      setHealth(null);
      setError(
        caught instanceof Error
          ? caught.message
          : "Karen Core is unavailable.",
      );
    }
  }, []);

  useEffect(() => {
    const initialRefresh = window.setTimeout(() => {
      void refresh();
    }, 0);

    const interval = window.setInterval(() => {
      void refresh();
    }, 15000);

    return () => {
      window.clearTimeout(initialRefresh);
      window.clearInterval(interval);
    };
  }, [refresh]);

  async function perform(
    busyKey: string,
    action: () => Promise<unknown>,
  ): Promise<void> {
    setBusyId(busyKey);
    setError(null);

    try {
      await action();
      await refresh();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The requested operation failed.",
      );
    } finally {
      setBusyId(null);
    }
  }

  function renderTask(
    task: WorkflowTask,
  ): ReactNode {
    return (
      <TaskCard
        key={task.id}
        task={task}
        busy={busyId === task.id}
        onApprove={() => {
          void perform(
            task.id,
            () => approveTask(task.id),
          );
        }}
        onReject={() => {
          void perform(
            task.id,
            () => rejectTask(task.id),
          );
        }}
        onFinalize={() => {
          void perform(
            task.id,
            () => finalizeSelfUpdate(task.id),
          );
        }}
      />
    );
  }

  function renderOverview(): ReactNode {
    return (
      <>
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Core status"
            value={health?.status ?? "Offline"}
            detail="FastAPI orchestration service"
            icon={<Activity size={19} />}
          />

          <MetricCard
            label="Memory"
            value={
              health
                ? `${health.memory.used_percent.toFixed(0)}%`
                : "—"
            }
            detail={
              health
                ? `${health.memory.available_gib.toFixed(1)} GiB available`
                : "No telemetry"
            }
            icon={<MemoryStick size={19} />}
          />

          <MetricCard
            label="Swap"
            value={
              health
                ? `${health.swap.used_percent.toFixed(0)}%`
                : "—"
            }
            detail={
              health
                ? `${health.swap.total_gib.toFixed(1)} GiB configured`
                : "No telemetry"
            }
            icon={<HardDrive size={19} />}
          />

          <MetricCard
            label="Workflow tasks"
            value={String(tasks.length)}
            detail={`${pendingTasks} awaiting approval`}
            icon={<Cpu size={19} />}
          />
        </section>

        <section className="glass-panel rounded-3xl p-6">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="font-semibold">
                Recent workflow activity
              </h2>
              <p className="mt-1 text-xs text-zinc-500">
                Latest plans, approvals and reviews
              </p>
            </div>

            <button
              type="button"
              aria-label="Refresh tasks"
              onClick={() => {
                void refresh();
              }}
              className="rounded-xl border border-white/10 p-2 text-zinc-400 transition hover:bg-white/5 hover:text-white"
            >
              <RefreshCw size={17} />
            </button>
          </div>

          <div className="space-y-3">
            {tasks.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 p-10 text-center text-sm text-zinc-500">
                No workflow tasks have been created.
              </div>
            ) : (
              tasks.slice(0, 4).map(renderTask)
            )}
          </div>
        </section>
      </>
    );
  }

  function renderSelfUpdate(): ReactNode {
    return (
      <section className="grid gap-5 xl:grid-cols-[1fr_1.35fr]">
        <div className="glass-panel rounded-3xl p-6">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-red-500/12 text-red-300">
              <Sparkles size={19} />
            </div>

            <div>
              <h2 className="font-semibold">
                Plan a self-update
              </h2>
              <p className="text-xs text-zinc-500">
                Nothing changes before approval.
              </p>
            </div>
          </div>

          <textarea
            value={prompt}
            onChange={(event) => {
              setPrompt(event.target.value);
            }}
            className="mt-5 min-h-52 w-full resize-y rounded-2xl border border-white/10 bg-black/30 p-4 text-sm leading-6 text-zinc-200 outline-none transition placeholder:text-zinc-600 focus:border-red-400/45"
            placeholder="Describe the update Karen should make..."
          />

          <button
            type="button"
            onClick={() => {
              const trimmedPrompt = prompt.trim();

              if (!trimmedPrompt) {
                return;
              }

              void perform(
                "create-plan",
                () => planSelfUpdate(trimmedPrompt),
              );
            }}
            disabled={
              busyId !== null || !prompt.trim()
            }
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-red-500 px-5 py-3 text-sm font-medium text-white transition hover:bg-red-400 disabled:opacity-50"
          >
            {busyId === "create-plan" ? (
              <LoaderCircle
                className="animate-spin"
                size={18}
              />
            ) : (
              <Sparkles size={18} />
            )}

            Generate update plan
          </button>

          <div className="mt-5 rounded-2xl border border-white/7 bg-black/20 p-4">
            <div className="flex items-center gap-2 text-xs font-medium text-zinc-300">
              <ShieldCheck
                size={15}
                className="text-red-300"
              />
              Safety policy
            </div>

            <p className="mt-2 text-xs leading-5 text-zinc-500">
              Karen requires a clean repository, creates a
              checkpoint, confines changes to the project and runs
              verification before allowing a commit.
            </p>
          </div>
        </div>

        <div className="glass-panel rounded-3xl p-6">
          <h2 className="font-semibold">
            Self-update history
          </h2>

          <p className="mt-1 text-xs text-zinc-500">
            Updates generated for Karen's own source code
          </p>

          <div className="mt-5 space-y-3">
            {selfUpdateTasks.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 p-10 text-center text-sm text-zinc-500">
                No classified self-update tasks yet.
              </div>
            ) : (
              selfUpdateTasks.map(renderTask)
            )}
          </div>
        </div>
      </section>
    );
  }

  function renderCodingTasks(): ReactNode {
    return (
      <section className="glass-panel rounded-3xl p-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="font-semibold">
              All coding tasks
            </h2>

            <p className="mt-1 text-xs text-zinc-500">
              {tasks.length} stored workflow records
            </p>
          </div>

          <button
            type="button"
            onClick={() => {
              void refresh();
            }}
            className="rounded-xl border border-white/10 p-2 text-zinc-400 hover:bg-white/5 hover:text-white"
          >
            <RefreshCw size={17} />
          </button>
        </div>

        <div className="space-y-3">
          {tasks.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 p-10 text-center text-sm text-zinc-500">
              No coding tasks available.
            </div>
          ) : (
            tasks.map(renderTask)
          )}
        </div>
      </section>
    );
  }

  function renderTools(): ReactNode {
    const tools = [
      {
        icon: TerminalSquare,
        name: "Restricted terminal",
        detail:
          "Read-only allowlisted commands with workspace isolation and timeouts.",
      },
      {
        icon: GitCommit,
        name: "Controlled Git",
        detail:
          "Status, diff, staging, commits, checkpoints and selected-file restore.",
      },
      {
        icon: FileCode2,
        name: "Workspace files",
        detail:
          "UTF-8 file inspection and confirmed writes with automatic backups.",
      },
      {
        icon: Cpu,
        name: "Local model",
        detail:
          "Ollama and Qwen Coder provide local planning, coding and review.",
      },
    ];

    return (
      <section className="grid gap-4 md:grid-cols-2">
        {tools.map((tool) => {
          const ToolIcon = tool.icon;

          return (
            <article
              key={tool.name}
              className="glass-panel rounded-3xl p-6"
            >
              <div className="grid size-11 place-items-center rounded-xl bg-red-500/12 text-red-300">
                <ToolIcon size={20} />
              </div>

              <h2 className="mt-5 font-semibold">
                {tool.name}
              </h2>

              <p className="mt-2 text-sm leading-6 text-zinc-500">
                {tool.detail}
              </p>
            </article>
          );
        })}

        <a
          href="http://127.0.0.1:8080/docs"
          target="_blank"
          rel="noreferrer"
          className="glass-panel rounded-3xl p-6 transition hover:border-red-400/30"
        >
          <div className="text-xs uppercase tracking-[0.2em] text-red-300">
            Developer interface
          </div>

          <h2 className="mt-3 text-xl font-semibold">
            Open Swagger API
          </h2>

          <p className="mt-2 text-sm text-zinc-500">
            Inspect and test every Karen Core endpoint.
          </p>
        </a>
      </section>
    );
  }

  function renderMemory(): ReactNode {
    return (
      <section className="grid gap-5 xl:grid-cols-[0.7fr_1.3fr]">
        <div className="glass-panel rounded-3xl p-6">
          <Database size={24} className="text-red-300" />

          <div className="mt-5 text-3xl font-semibold">
            {contextFiles.length}
          </div>

          <p className="mt-1 text-sm text-zinc-500">
            Unique indexed context files used by saved tasks
          </p>

          <div className="mt-6 text-3xl font-semibold">
            {tasks.length}
          </div>

          <p className="mt-1 text-sm text-zinc-500">
            Persistent workflow records
          </p>
        </div>

        <div className="glass-panel rounded-3xl p-6">
          <h2 className="font-semibold">
            Recent project context
          </h2>

          <div className="mt-5 max-h-[540px] space-y-2 overflow-y-auto">
            {contextFiles.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 p-10 text-center text-sm text-zinc-500">
                No project context has been recorded.
              </div>
            ) : (
              contextFiles.map((file) => (
                <div
                  key={file}
                  className="rounded-xl border border-white/7 bg-black/20 px-4 py-3 font-mono text-xs text-zinc-400"
                >
                  {file}
                </div>
              ))
            )}
          </div>
        </div>
      </section>
    );
  }

  function renderSecurity(): ReactNode {
    const policies = [
      "Commands must match an explicit allowlist.",
      "All file access stays inside ~/Workspace.",
      "Secret-like paths and private keys are rejected.",
      "Self-updates require a clean Git repository.",
      "File modifications require explicit approval.",
      "Git checkpoints are created before coding workflows.",
      "Tests and compilation run before AI review.",
      "Unrestricted shell execution and deletion remain disabled.",
    ];

    return (
      <section className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="glass-panel rounded-3xl p-6">
          <div className="flex items-center gap-3">
            <div className="grid size-11 place-items-center rounded-xl bg-emerald-500/12 text-emerald-300">
              <ShieldCheck size={22} />
            </div>

            <div>
              <h2 className="font-semibold">
                Safety kernel active
              </h2>

              <p className="text-xs text-zinc-500">
                Approval-gated local execution
              </p>
            </div>
          </div>

          <div className="mt-6 space-y-3">
            {policies.map((policy) => (
              <div
                key={policy}
                className="flex items-start gap-3 rounded-xl border border-white/7 bg-black/20 p-4"
              >
                <CheckCircle2
                  size={16}
                  className="mt-0.5 shrink-0 text-emerald-400"
                />

                <span className="text-sm text-zinc-400">
                  {policy}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel rounded-3xl p-6">
          <KeyRound size={24} className="text-red-300" />

          <h2 className="mt-5 font-semibold">
            Protected operations
          </h2>

          <div className="mt-5 space-y-3 text-sm text-zinc-500">
            <div>System configuration</div>
            <div>Credential and secret files</div>
            <div>Arbitrary deletion</div>
            <div>Unapproved Git pushes</div>
            <div>Unrestricted root commands</div>
          </div>
        </div>
      </section>
    );
  }

  function renderPage(): ReactNode {
    switch (activePage) {
      case "self-update":
        return renderSelfUpdate();

      case "coding-tasks":
        return renderCodingTasks();

      case "tools":
        return renderTools();

      case "memory":
        return renderMemory();

      case "security":
        return renderSecurity();

      default:
        return renderOverview();
    }
  }

  const currentPage = pageCopy[activePage];

  return (
    <div className="min-h-screen text-zinc-100">
      <div className="mx-auto grid max-w-[1600px] grid-cols-1 gap-5 p-4 md:grid-cols-[220px_minmax(0,1fr)] md:p-5 xl:grid-cols-[240px_minmax(0,1fr)] xl:p-6">
        <aside className="glass-panel flex min-h-0 flex-col rounded-3xl p-5 md:sticky md:top-5 md:h-[calc(100vh-2.5rem)]">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-red-500/15 text-red-300">
              <BrainCircuit size={22} />
            </div>

            <div>
              <div className="font-semibold tracking-wide">
                KAREN
              </div>

              <div className="text-xs text-zinc-500">
                Control Center 1.2
              </div>
            </div>
          </div>

          <nav className="mt-10 space-y-2 text-sm">
            {navigationItems.map((item) => {
              const NavigationIcon = item.icon;
              const isActive = activePage === item.id;

              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    setActivePage(item.id);
                  }}
                  className={[
                    "flex w-full items-center gap-3",
                    "rounded-xl px-3 py-3 text-left transition",
                    isActive
                      ? "bg-red-500/12 text-red-200"
                      : "text-zinc-400 hover:bg-white/5 hover:text-white",
                  ].join(" ")}
                >
                  <NavigationIcon size={18} />
                  {item.label}
                </button>
              );
            })}
          </nav>

          <div className="mt-auto rounded-2xl border border-white/7 bg-black/20 p-4">
            <div className="flex items-center gap-2 text-sm">
              <span
                className={[
                  "size-2 rounded-full",
                  health ? "bg-emerald-400" : "bg-red-400",
                ].join(" ")}
              />

              {health
                ? "Karen Core online"
                : "Karen Core offline"}
            </div>

            <div className="mt-2 text-xs text-zinc-500">
              Local-first · Approval gated
            </div>
          </div>
        </aside>

        <main className="min-w-0 space-y-5">
          <header className="glass-panel flex flex-col items-center justify-between gap-7 rounded-3xl px-7 py-8 md:flex-row">
            <div>
              <div className="mb-2 text-xs font-medium uppercase tracking-[0.28em] text-red-300">
                {currentPage.eyebrow}
              </div>

              <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">
                {currentPage.title}
              </h1>

              <p className="mt-3 max-w-xl text-sm leading-6 text-zinc-400">
                {currentPage.description}
              </p>
            </div>

            <div className="flex min-w-[190px] flex-col items-center py-3">
              <div className="karen-orb" />

              <div className="mt-9 text-xs uppercase tracking-[0.25em] text-zinc-500">
                Core active
              </div>
            </div>
          </header>

          {error && (
            <div className="rounded-2xl border border-red-400/25 bg-red-500/10 px-5 py-4 text-sm text-red-200">
              {error}
            </div>
          )}

          {renderPage()}
        </main>
      </div>
    </div>
  );
}

export default App;
