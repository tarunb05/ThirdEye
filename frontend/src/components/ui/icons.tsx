// ─── Inline SVG icons (dependency-free) ───
type IconProps = { size?: number; className?: string };

function Svg({ size = 16, className = "", children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.6}
      className={className}
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export const EyeIcon = (p: IconProps) => (
  <Svg {...p}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </Svg>
);

export const CheckIcon = (p: IconProps) => (
  <Svg {...p} className={`${p.className ?? ""}`}>
    <path strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
  </Svg>
);

export const ShieldCheckIcon = (p: IconProps) => (
  <Svg {...p}>
    <path strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M12 2.714l7.5 2.5v5.072c0 4.51-3.027 8.65-7.5 9.714C7.527 18.936 4.5 14.796 4.5 10.286V5.214l7.5-2.5z" />
  </Svg>
);

export const AlertIcon = (p: IconProps) => (
  <Svg {...p}>
    <path strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m0 3.75h.008M11.25 4.533l-8.4 14.55A1.5 1.5 0 004.15 21.3h15.7a1.5 1.5 0 001.3-2.217l-8.4-14.55a1.5 1.5 0 00-2.6 0z" />
  </Svg>
);

export const BoltIcon = (p: IconProps) => (
  <Svg {...p}>
    <path strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
  </Svg>
);

export const ChipIcon = (p: IconProps) => (
  <Svg {...p}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 3v1.5M12 3v1.5m3.75-1.5v1.5M8.25 19.5V21m3.75-1.5V21m3.75-1.5V21M3 8.25h1.5M3 12h1.5m-1.5 3.75h1.5M19.5 8.25H21m-1.5 3.75H21m-1.5 3.75H21M5.25 6.75h13.5v10.5H5.25z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 9.75h6v4.5H9z" />
  </Svg>
);

export const GridIcon = (p: IconProps) => (
  <Svg {...p}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
  </Svg>
);

export const ScanIcon = (p: IconProps) => (
  <Svg {...p}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 7.5V6a3 3 0 013-3h1.5M21 7.5V6a3 3 0 00-3-3h-1.5M3 16.5V18a3 3 0 003 3h1.5M21 16.5V18a3 3 0 01-3 3h-1.5M3 12h18" />
  </Svg>
);

export const FlowIcon = (p: IconProps) => (
  <Svg {...p}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
    <circle cx="7" cy="6.75" r="1.4" fill="currentColor" stroke="none" />
    <circle cx="14" cy="12" r="1.4" fill="currentColor" stroke="none" />
    <circle cx="10" cy="17.25" r="1.4" fill="currentColor" stroke="none" />
  </Svg>
);

export const ChartIcon = (p: IconProps) => (
  <Svg {...p}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
  </Svg>
);

export const HistoryIcon = (p: IconProps) => (
  <Svg {...p}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
  </Svg>
);

export const HomeIcon = (p: IconProps) => (
  <Svg {...p}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75" />
  </Svg>
);

export const UploadIcon = (p: IconProps) => (
  <Svg {...p}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 16V4m0 0L8 8m4-4 4 4M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
  </Svg>
);

export const ArrowRightIcon = (p: IconProps) => (
  <Svg {...p}>
    <path strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
  </Svg>
);

export const LogoutIcon = (p: IconProps) => (
  <Svg {...p}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
  </Svg>
);

export const TrendUpIcon = (p: IconProps) => (
  <Svg {...p}>
    <path strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.306a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.281m5.94 2.28l-2.28 5.941" />
  </Svg>
);

export const TrendDownIcon = (p: IconProps) => (
  <Svg {...p}>
    <path strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" d="M2.25 6L9 12.75l4.286-4.286a11.948 11.948 0 014.306 6.43l.776 2.898m0 0l3.182-5.511m-3.182 5.51l-5.511-3.181" />
  </Svg>
);

// ─── Third-Eye mark — a single all-seeing eye inside a guardian ring ───
export function ThirdEyeMark({ size = 28, className = "" }: IconProps) {
  // Subtle radial ticks around the eye — the watchful periphery.
  const ticks = Array.from({ length: 8 }, (_, i) => {
    const a = (i / 8) * Math.PI * 2 - Math.PI / 2;
    return { x: 12 + Math.cos(a) * 9.6, y: 12 + Math.sin(a) * 9.6 };
  });
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <circle cx="12" cy="12" r="11" stroke="currentColor" strokeOpacity="0.2" strokeWidth="0.75" />
      {ticks.map((t, i) => (
        <circle key={i} cx={t.x} cy={t.y} r="0.7" fill="currentColor" fillOpacity={0.4} />
      ))}
      {/* Almond eye outline */}
      <path
        d="M3.4 12C5.6 8.4 8.6 6.6 12 6.6S18.4 8.4 20.6 12C18.4 15.6 15.4 17.4 12 17.4S5.6 15.6 3.4 12Z"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinejoin="round"
      />
      {/* Iris + pupil */}
      <circle cx="12" cy="12" r="3.3" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="12" cy="12" r="1.5" fill="currentColor" />
    </svg>
  );
}
