import type { ButtonHTMLAttributes, ReactNode } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  icon?: ReactNode;
};

export function TerminalButton({ icon, className = "", children, ...props }: Props) {
  const classes = [className, icon ? "has-icon" : ""].filter(Boolean).join(" ");
  return (
    <button className={classes} {...props}>
      {icon ? <span className="button-icon">{icon}</span> : null}
      {children}
    </button>
  );
}
