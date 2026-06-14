"use client";
import { useState } from "react";
import { useSystemStatus, useMMState } from "@/hooks/usePolling";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { AlertTriangle, Zap, Pause, Play, DollarSign } from "lucide-react";

function ConfirmModal({
  open, title, description, confirmLabel, confirmClass, onConfirm, onCancel, children,
}: {
  open: boolean; title: string; description: string;
  confirmLabel: string; confirmClass: string;
  onConfirm: () => void; onCancel: () => void;
  children?: React.ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center p-4">
      <div className="fixed inset-0 bg-black/60" onClick={onCancel} />
      <div className="relative z-10 w-full max-w-sm rounded-2xl border border-border bg-surface p-6">
        <div className="mb-1 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-orange" />
          <h3 className="font-semibold text-fg">{title}</h3>
        </div>
        <p className="mb-4 text-sm text-fg-3">{description}</p>
        {children}
        <div className="flex gap-2">
          <button onClick={onCancel}
            className="flex-1 rounded-lg border border-border py-2.5 text-sm font-semibold text-fg-3 hover:bg-surface2 transition-colors">
            Cancel
          </button>
          <button onClick={onConfirm}
            className={cn("flex-1 rounded-lg py-2.5 text-sm font-semibold transition-colors", confirmClass)}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ControlPage() {
  const qc = useQueryClient();
  const { data: sys } = useSystemStatus();
  const { data: state } = useMMState();

  const [showKill, setShowKill] = useState(false);
  const [showLive, setShowLive] = useState(false);
  const [capital, setCapital] = useState(1000);

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["system-status"] });
    qc.invalidateQueries({ queryKey: ["mm-state"] });
  };

  async function kill() {
    try {
      await api.mmKill();
      toast.success("Kill switch armed — all quotes cancelled");
      setShowKill(false);
      refresh();
    } catch { toast.error("Kill failed"); }
  }

  async function resume() {
    try {
      await api.mmResume();
      toast.success("Trading resumed");
      refresh();
    } catch { toast.error("Resume failed"); }
  }

  async function goLive() {
    try {
      await api.mmGoLive(capital);
      toast.success(`LIVE — $${capital} deployed`, { duration: 5000 });
      setShowLive(false);
      refresh();
    } catch { toast.error("Go live failed"); }
  }

  async function goPaper() {
    try {
      await api.mmGoPaper();
      toast.success("Switched to paper mode");
      refresh();
    } catch { toast.error("Failed"); }
  }

  const isLive = !sys?.paper_mode;
  const isKilled = sys?.kill_switch;
  const isCB = sys?.circuit_breaker;

  return (
    <div className="max-w-md px-4 pb-10 pt-6">
      {/* Current status */}
      <div className={cn(
        "mb-6 flex items-center gap-4 rounded-xl border p-4",
        isKilled || isCB ? "border-red/40 bg-red/10" :
        isLive           ? "border-green/40 bg-green/10" :
                           "border-orange/40 bg-orange/10"
      )}>
        <div className={cn(
          "flex h-10 w-10 items-center justify-center rounded-full",
          isKilled || isCB ? "bg-red/20" : isLive ? "bg-green/20" : "bg-orange/20"
        )}>
          {isLive && !isKilled ? <Zap className="h-5 w-5 text-green" /> :
           <Pause className="h-5 w-5 text-orange" />}
        </div>
        <div>
          <p className={cn("text-lg font-bold",
            isKilled || isCB ? "text-red" : isLive ? "text-green" : "text-orange"
          )}>
            {isKilled ? "KILLED" : isCB ? "CIRCUIT BREAKER" : isLive ? "LIVE TRADING" : "PAPER MODE"}
          </p>
          <p className="text-xs text-fg-3">
            {isLive && !isKilled
              ? `$${state?.capital_usd?.toFixed(0) ?? "—"} deployed`
              : "No real orders being placed"}
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="space-y-3">
        {/* Kill switch */}
        <button
          onClick={() => setShowKill(true)}
          disabled={isKilled}
          className={cn(
            "flex w-full items-center gap-3 rounded-xl border p-4 text-left transition-colors",
            isKilled
              ? "border-border bg-muted opacity-50 cursor-not-allowed"
              : "border-red/30 bg-red/10 hover:bg-red/15"
          )}
        >
          <AlertTriangle className="h-5 w-5 shrink-0 text-red" />
          <div>
            <p className="font-semibold text-red">Kill Switch</p>
            <p className="text-xs text-fg-3">Cancel all orders, halt trading immediately</p>
          </div>
        </button>

        {/* Resume */}
        <button
          onClick={resume}
          disabled={!isKilled}
          className={cn(
            "flex w-full items-center gap-3 rounded-xl border p-4 text-left transition-colors",
            !isKilled
              ? "border-border bg-surface opacity-50 cursor-not-allowed"
              : "border-green/30 bg-green/10 hover:bg-green/15"
          )}
        >
          <Play className="h-5 w-5 shrink-0 text-green" />
          <div>
            <p className="font-semibold text-green">Resume Trading</p>
            <p className="text-xs text-fg-3">Disarm kill switch and resume quoting</p>
          </div>
        </button>

        {/* Go Live */}
        {!isLive && (
          <button
            onClick={() => setShowLive(true)}
            className="flex w-full items-center gap-3 rounded-xl border border-blue/30 bg-blue/10 p-4 text-left transition-colors hover:bg-blue/15"
          >
            <DollarSign className="h-5 w-5 shrink-0 text-blue" />
            <div>
              <p className="font-semibold text-blue">Go Live</p>
              <p className="text-xs text-fg-3">Deploy real capital — places actual orders</p>
            </div>
          </button>
        )}

        {/* Return to paper */}
        {isLive && (
          <button
            onClick={goPaper}
            className="flex w-full items-center gap-3 rounded-xl border border-border bg-surface p-4 text-left transition-colors hover:bg-surface2"
          >
            <Pause className="h-5 w-5 shrink-0 text-muted-fg" />
            <div>
              <p className="font-semibold text-fg-2">Return to Paper</p>
              <p className="text-xs text-fg-3">Switch back to simulation mode</p>
            </div>
          </button>
        )}
      </div>

      {/* Kill confirm */}
      <ConfirmModal
        open={showKill}
        title="Arm kill switch?"
        description="All resting maker orders will be cancelled immediately. Trading will halt until you manually resume."
        confirmLabel="Kill All Orders"
        confirmClass="bg-red text-white hover:bg-red/80"
        onConfirm={kill}
        onCancel={() => setShowKill(false)}
      />

      {/* Go Live confirm */}
      <ConfirmModal
        open={showLive}
        title="Go live with real capital?"
        description="This will place REAL orders on the Kalshi exchange. Make sure you have run a backtest and paper traded first."
        confirmLabel="Confirm Go Live"
        confirmClass="bg-blue text-white hover:bg-blue/80"
        onConfirm={goLive}
        onCancel={() => setShowLive(false)}
      >
        <div className="mb-4 flex items-center gap-3 rounded-lg border border-border bg-surface2 px-3 py-2.5">
          <span className="text-sm text-fg-3">Capital $</span>
          <input
            type="number"
            value={capital}
            onChange={(e) => setCapital(Number(e.target.value))}
            min={100} max={1000000} step={100}
            className="flex-1 bg-transparent font-mono text-sm font-bold text-fg focus:outline-none tabular"
          />
        </div>
      </ConfirmModal>
    </div>
  );
}
