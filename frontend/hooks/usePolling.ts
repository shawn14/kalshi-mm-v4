"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

const FAST = 2_000;   // 2s — live trading data
const SLOW = 15_000;  // 15s — research data

export function useMMState() {
  return useQuery({ queryKey: ["mm-state"], queryFn: api.mmState, refetchInterval: FAST });
}

export function useMMQuotes() {
  return useQuery({ queryKey: ["mm-quotes"], queryFn: api.mmQuotes, refetchInterval: FAST });
}

export function useMMInventory() {
  return useQuery({ queryKey: ["mm-inventory"], queryFn: api.mmInventory, refetchInterval: FAST });
}

export function useSystemStatus() {
  return useQuery({ queryKey: ["system-status"], queryFn: api.systemStatus, refetchInterval: FAST });
}

export function useBacktestResults() {
  return useQuery({ queryKey: ["backtest"], queryFn: api.backtestResults, refetchInterval: SLOW });
}

export function usePaperPerformance() {
  return useQuery({ queryKey: ["paper"], queryFn: api.paperPerformance, refetchInterval: SLOW });
}

export function useSeriesScores() {
  return useQuery({ queryKey: ["series-scores"], queryFn: api.seriesScores, refetchInterval: 60_000 });
}
