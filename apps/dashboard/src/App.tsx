import {
  Activity,
  BrainCircuit,
  CheckCircle2,
  Code2,
  Cpu,
  Database,
  GitCommit,
  HardDrive,
  LoaderCircle,
  MemoryStick,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  XCircle,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

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

function statusClasses(status: TaskStatus): string {
  switch (status) {
    case "completed":
    case "committed":
      return [
        "border-emerald-400/30",
        "bg-emerald-400/10",
        "text-emerald-300",
      ].join(" ");

    case "running":
      return [
        "border-sky-400/30",
        "bg-sky-400/10",
        "text-sky-300",
      ].join(" ");

    case "needs_review":
      return [
        "border-amber-400/30",
        "bg-amber-400/10",
        "text-amber-300",
      ].join(" ");

    case "failed":
    case "rejected":
      return [
        "border-red-400/30",
        "bg-red-400/10",
        "text-red-300",
      ].join(" ");

    default:
      return [
        "border-zinc-400/20",
        "bg-zinc-400/10",
        "text-zinc-300",
      ].join(" ");
  }
}

function formatStatus(status: TaskStatus): string {
  return status.replaceAll("_", " ");
}

function formatTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
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
            className={[
              "truncate rounded-lg bg-white/[0.035]",
              "px-3 py-2 font-mono text-[11px]",
              "text-zinc-400",
            ].join(" ")}
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
              className={[
                "flex items-center gap-1.5 rounded-lg",
                "bg-emerald-500/15 px-3 py-2",
                "text-xs text-emerald-300 transition",
                "hover:bg-emerald-500/25",
                "disabled:opacity-50",
              ].join(" ")}
            >
              <Play size={14} />
              Approve
            </button>

            <button
              type="button"
              onClick={onReject}
              disabled={busy}
              className={[
                "flex items-center gap-1.5 rounded-lg",
                "bg-red-500/10 px-3 py-2",
                "text-xs text-red-300 transition",
                "hover:bg-red-500/20",
                "disabled:opacity-50",
              ].join(" ")}
            >
              <XCircle size={14} />
              Reject
            </button>
          </>
        )}

        {task.status === "completed" && (
          <>
            <button
              type="button"
              onClick={onFinalize}
              disabled={busy}
              className={[
                "flex items-center gap-1.5 rounded-lg",
                "bg-red-500/15 px-3 py-2",
                "text-xs text-red-200 transition",
                "hover:bg-red-500/25",
                "disabled:opacity-50",
              ].join(" ")}
            >
              <GitCommit size={14} />
              Finalize commit
            </button>

            <span className="flex items-center gap-1.5 px-2 py-2 text-xs text-emerald-400">
              <CheckCircle2 size={14} />
              Verification passed
            </span>
          </>
        )}

        {busy && (
          <LoaderCircle
            className="animate-spin text-zinc-400"
            size={17}
          />
        )}
      </div>

      <div className="mt-3 text-[10px] text-zinc-700">
        Updated {formatTime(task.updated_at)}
      </div>
    </article>
  );
}

interface NavigationItem {
  icon: LucideIcon;
  label: string;
}

const navigationItems: NavigationItem[] = [
  {
    icon: Activity,
    label: "Overview",
  },
  {
    icon: Sparkles,
    label: "Self Update",
  },
  {
    icon: Code2,
    label: "Coding Tasks",
  },
  {
    icon: TerminalSquare,
    label: "Tools",
  },
  {
    icon: Database,
    label: "Memory",
  },
  {
    icon: ShieldCheck,
    label: "Security",
  },
];

function App() {
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

  async function createUpdatePlan(): Promise<void> {
    const trimmedPrompt = prompt.trim();

    if (!trimmedPrompt) {
      return;
    }

    await perform(
      "create-plan",
      () => planSelfUpdate(trimmedPrompt),
    );
  }

  return (
    <div className="min-h-screen text-zinc-100">
      <div
        className={[
          "mx-auto grid max-w-[1600px] grid-cols-1 gap-5",
          "p-4 md:grid-cols-[220px_minmax(0,1fr)] md:p-5",
          "xl:grid-cols-[240px_minmax(0,1fr)] xl:p-6",
        ].join(" ")}
      >
        <aside
          className={[
            "glass-panel flex min-h-0 flex-col rounded-3xl p-5",
            "md:sticky md:top-5 md:h-[calc(100vh-2.5rem)]",
          ].join(" ")}
        >
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-red-500/15 text-red-300">
              <BrainCircuit size={22} />
            </div>

            <div>
              <div className="font-semibold tracking-wide">
                KAREN
              </div>
              <div className="text-xs text-zinc-500">
                Control Center 1.1
              </div>
            </div>
          </div>

          <nav className="mt-10 space-y-2 text-sm">
            {navigationItems.map((item, index) => {
            const NavigationIcon = item.icon;

            return (
              <button
              key={item.label}
              type="button"
              className={[
                "flex w-full items-center gap-3",
                "rounded-xl px-3 py-3 text-left transition",
                index === 0
                ? "bg-red-500/12 text-red-200"
                : [
                    "text-zinc-400",
                    "hover:bg-white/5 hover:text-white",
                  ].join(" "),
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
          <header
            className={[
              "glass-panel flex flex-col items-center",
              "justify-between gap-7 rounded-3xl",
              "px-7 py-8 md:flex-row",
            ].join(" ")}
          >
            <div>
              <div className="mb-2 text-xs font-medium uppercase tracking-[0.28em] text-red-300">
                Local AI Engineering System
              </div>

              <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">
                Karen Control Center
              </h1>

              <p className="mt-3 max-w-xl text-sm leading-6 text-zinc-400">
                Plan, approve, verify and finalize coding updates
                without giving the model unrestricted system access.
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

          <section className="grid gap-5 xl:grid-cols-[1.02fr_1.45fr]">
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
                    Nothing changes before you approve the plan.
                  </p>
                </div>
              </div>

              <textarea
                value={prompt}
                onChange={(event) => {
                  setPrompt(event.target.value);
                }}
                className={[
                  "mt-5 min-h-48 w-full resize-y rounded-2xl",
                  "border border-white/10 bg-black/30 p-4",
                  "text-sm leading-6 text-zinc-200 outline-none",
                  "transition placeholder:text-zinc-600",
                  "focus:border-red-400/45",
                ].join(" ")}
                placeholder="Describe the update Karen should make..."
              />

              <button
                type="button"
                onClick={() => {
                  void createUpdatePlan();
                }}
                disabled={
                  busyId !== null || !prompt.trim()
                }
                className={[
                  "mt-4 flex w-full items-center",
                  "justify-center gap-2 rounded-xl",
                  "bg-red-500 px-5 py-3",
                  "text-sm font-medium text-white transition",
                  "hover:bg-red-400",
                  "disabled:opacity-50",
                ].join(" ")}
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
                  <ShieldCheck size={15} className="text-red-300" />
                  Safety policy
                </div>

                <p className="mt-2 text-xs leading-5 text-zinc-500">
                  Karen creates a Git checkpoint, limits changes to
                  the selected project, runs verification and asks
                  for approval before finalizing the commit.
                </p>
              </div>
            </div>

            <div className="glass-panel rounded-3xl p-6">
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <h2 className="font-semibold">
                    Workflow activity
                  </h2>

                  <p className="mt-1 text-xs text-zinc-500">
                    Recent plans, approvals and reviews
                  </p>
                </div>

                <button
                  type="button"
                  aria-label="Refresh tasks"
                  onClick={() => {
                    void refresh();
                  }}
                  className={[
                    "rounded-xl border border-white/10 p-2",
                    "text-zinc-400 transition",
                    "hover:bg-white/5 hover:text-white",
                  ].join(" ")}
                >
                  <RefreshCw size={17} />
                </button>
              </div>

              <div className="max-h-[610px] space-y-3 overflow-y-auto pr-1">
                {tasks.length === 0 && (
                  <div className="rounded-2xl border border-dashed border-white/10 p-10 text-center text-sm text-zinc-500">
                    No workflow tasks have been created.
                  </div>
                )}

                {tasks.slice(0, 12).map((task) => (
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
                ))}
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
