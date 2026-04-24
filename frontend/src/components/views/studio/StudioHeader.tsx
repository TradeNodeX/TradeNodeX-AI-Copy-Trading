import { RefreshCcw } from "lucide-react";

import { SectionHeader } from "../../primitives/SectionHeader";
import { TerminalButton } from "../../primitives/TerminalButton";

type Props = {
  eyebrow: string;
  title: string;
  onRefreshInstruments: () => void;
  refreshLabel: string;
  exchange: string;
  environment: string;
  productType: string;
};

export function StudioHeader(props: Props) {
  return (
    <>
      <SectionHeader
        eyebrow={props.eyebrow}
        title={props.title}
        actions={
          <TerminalButton className="secondary" type="button" onClick={props.onRefreshInstruments} icon={<RefreshCcw size={14} />}>
            {props.refreshLabel}
          </TerminalButton>
        }
      />
      <div className="studio-top terminal-surface">
        <div className="studio-title">
          <h3>{props.exchange} Futures</h3>
          <div className="studio-links">
            <a href="#" onClick={(event) => event.preventDefault()}>Add API Key</a>
            <span>|</span>
            <a href="#" onClick={(event) => event.preventDefault()}>How-to</a>
            <span>|</span>
            <a href="#" onClick={(event) => event.preventDefault()}>Register</a>
          </div>
        </div>
        <div className="studio-env">{props.environment} · {props.productType}</div>
      </div>
    </>
  );
}
