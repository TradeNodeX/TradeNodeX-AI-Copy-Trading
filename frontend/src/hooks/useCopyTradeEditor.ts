import { useEffect, useMemo, useState } from "react";

import { initialCopyTradeDraft, type CopyTradeDraft } from "../lib/app-model";
import type { CopyTrade } from "../types";

export function useCopyTradeEditor(copyTrades: CopyTrade[]) {
  const [selectedCopyTradeId, setSelectedCopyTradeId] = useState<string | null>(null);
  const [copyTradeDraft, setCopyTradeDraft] = useState<CopyTradeDraft>(initialCopyTradeDraft());

  const selectedCopyTrade = useMemo(
    () => copyTrades.find((item) => item.id === selectedCopyTradeId) ?? null,
    [copyTrades, selectedCopyTradeId]
  );

  useEffect(() => {
    if (selectedCopyTrade) {
      setCopyTradeDraft({
        id: selectedCopyTrade.id,
        name: selectedCopyTrade.name,
        signal_source_id: selectedCopyTrade.signal_source_id,
        follower_account_id: selectedCopyTrade.follower_account_id,
        copy_mode: selectedCopyTrade.copy_mode,
        scale_factor: selectedCopyTrade.scale_factor,
        override_leverage: selectedCopyTrade.override_leverage ? String(selectedCopyTrade.override_leverage) : "",
        command_template: selectedCopyTrade.command_template ?? "",
        notes: selectedCopyTrade.notes ?? "",
        enabled: selectedCopyTrade.enabled
      });
    } else {
      setCopyTradeDraft(initialCopyTradeDraft());
    }
  }, [selectedCopyTrade]);

  const resetCopyTradeEditor = () => {
    setSelectedCopyTradeId(null);
    setCopyTradeDraft(initialCopyTradeDraft());
  };

  return {
    selectedCopyTradeId,
    setSelectedCopyTradeId,
    selectedCopyTrade,
    copyTradeDraft,
    setCopyTradeDraft,
    resetCopyTradeEditor
  };
}
