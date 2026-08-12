type IconProps = { className?: string };

const base = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export const IconHome = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M3 11.5 12 4l9 7.5" />
    <path d="M5.5 10v9a1 1 0 0 0 1 1H9a1 1 0 0 0 1-1v-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v4a1 1 0 0 0 1 1h2.5a1 1 0 0 0 1-1v-9" />
  </svg>
);

export const IconBook = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15.5H6.5A2.5 2.5 0 0 0 4 21V5.5Z" />
    <path d="M4 18.5A2.5 2.5 0 0 1 6.5 16H20" />
  </svg>
);

export const IconLayers = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="m12 3 9 5-9 5-9-5 9-5Z" />
    <path d="m3 13 9 5 9-5" />
  </svg>
);

export const IconShuffle = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M3 6h3.5c2 0 3 1 4.5 3" />
    <path d="M3 18h3.5c2 0 3-1 4.5-3" />
    <path d="M14 6h3.2c1.6 0 2.4.6 3.3 1.8" />
    <path d="M14 18h3.2c1.6 0 2.4-.6 3.3-1.8" />
    <path d="m18 3 3 3-3 3" />
    <path d="m18 15 3 3-3 3" />
  </svg>
);

export const IconMessage = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M4 5h16v11H8l-4 4V5Z" />
  </svg>
);

export const IconHeadphones = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M4 14v-2a8 8 0 0 1 16 0v2" />
    <rect x="3" y="14" width="4.5" height="6" rx="1.5" />
    <rect x="16.5" y="14" width="4.5" height="6" rx="1.5" />
  </svg>
);

export const IconCheckSquare = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <rect x="3.5" y="3.5" width="17" height="17" rx="3" />
    <path d="m8 12 2.5 2.5L16 9" />
  </svg>
);

export const IconPencil = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M4 20.5 4.8 16 16.4 4.4a2 2 0 0 1 2.8 0l.4.4a2 2 0 0 1 0 2.8L8 19.2l-4 1.3Z" />
    <path d="m14 6.5 3 3" />
  </svg>
);

export const IconChart = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M4 20V10" />
    <path d="M11 20V4" />
    <path d="M18 20v-7" />
    <path d="M3 20h18" />
  </svg>
);

export const IconPlay = ({ className }: IconProps) => (
  <svg {...base} viewBox="0 0 24 24" fill="currentColor" stroke="none" className={className}>
    <path d="M8 5.5v13l11-6.5-11-6.5Z" />
  </svg>
);

export const IconPause = ({ className }: IconProps) => (
  <svg {...base} viewBox="0 0 24 24" fill="currentColor" stroke="none" className={className}>
    <rect x="6" y="5" width="4.5" height="14" rx="1" />
    <rect x="13.5" y="5" width="4.5" height="14" rx="1" />
  </svg>
);

export const IconVolume = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M4 9.5h3.5L12 6v12l-4.5-3.5H4v-5Z" />
    <path d="M16 9a3.5 3.5 0 0 1 0 6" />
    <path d="M18.3 6.7a7 7 0 0 1 0 10.6" />
  </svg>
);

export const IconMenu = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M4 7h16" />
    <path d="M4 12h16" />
    <path d="M4 17h16" />
  </svg>
);

export const IconSun = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <circle cx="12" cy="12" r="4.2" />
    <path d="M12 3v2.2M12 18.8V21M4.9 4.9l1.6 1.6M17.5 17.5l1.6 1.6M3 12h2.2M18.8 12H21M4.9 19.1l1.6-1.6M17.5 6.5l1.6-1.6" />
  </svg>
);

export const IconMoon = ({ className }: IconProps) => (
  <svg {...base} viewBox="0 0 24 24" fill="currentColor" stroke="none" className={className}>
    <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" />
  </svg>
);

export const IconCheck = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="m5 12.5 4.5 4.5L19 7" />
  </svg>
);

export const IconX = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="m6 6 12 12M18 6 6 18" />
  </svg>
);

export const IconFlame = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M12 3c1 3-3 4-3 7.5a3 3 0 0 0 6 0c1 0 2 1 2 3a5 5 0 1 1-10 0c0-4 2-4 3-7.5.4-1.4.7-2 2-3Z" />
  </svg>
);

export const IconStar = ({ className }: IconProps) => (
  <svg {...base} viewBox="0 0 24 24" fill="currentColor" stroke="none" className={className}>
    <path d="M12 2.5 14.8 9l7 .6-5.3 4.6 1.6 6.8L12 17.7 5.9 21l1.6-6.8L2.2 9.6l7-.6L12 2.5Z" />
  </svg>
);

export const IconArrowRight = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M4 12h15" />
    <path d="m13 6 6 6-6 6" />
  </svg>
);

export const IconRefresh = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M4 12a8 8 0 0 1 14-5.3L21 9" />
    <path d="M21 4v5h-5" />
    <path d="M20 12a8 8 0 0 1-14 5.3L3 15" />
    <path d="M3 20v-5h5" />
  </svg>
);

/* --- Icons added for review, achievements, settings and the command palette --- */

export const IconSearch = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.5-3.5" />
  </svg>
);

export const IconSettings = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
  </svg>
);

export const IconTrophy = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M7 4h10v5a5 5 0 0 1-10 0V4Z" />
    <path d="M7 6H4.5A1.5 1.5 0 0 0 3 7.5C3 9.4 4.6 11 6.5 11H7" />
    <path d="M17 6h2.5A1.5 1.5 0 0 1 21 7.5c0 1.9-1.6 3.5-3.5 3.5H17" />
    <path d="M12 14v3" />
    <path d="M8.5 20h7l-.7-2.5h-5.6L8.5 20Z" />
  </svg>
);

export const IconBolt = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M13 2 4.5 13.5H11L10 22l8.5-11.5H12L13 2Z" />
  </svg>
);

export const IconBookmark = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M6 3.5h12v17l-6-4-6 4v-17Z" />
  </svg>
);

export const IconBookmarkFilled = ({ className }: IconProps) => (
  <svg {...base} className={className} fill="currentColor">
    <path d="M6 3.5h12v17l-6-4-6 4v-17Z" />
  </svg>
);

export const IconAlert = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7.5v5.5" />
    <path d="M12 16.2v.3" />
  </svg>
);

export const IconInfo = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5.5" />
    <path d="M12 7.6v.3" />
  </svg>
);

export const IconDownload = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M12 3.5v11" />
    <path d="m7.5 10.5 4.5 4.5 4.5-4.5" />
    <path d="M4.5 19.5h15" />
  </svg>
);

export const IconUpload = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M12 15.5v-11" />
    <path d="m7.5 8.5 4.5-4.5 4.5 4.5" />
    <path d="M4.5 19.5h15" />
  </svg>
);

export const IconCalendar = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <rect x="3.5" y="5" width="17" height="15.5" rx="2" />
    <path d="M3.5 9.5h17" />
    <path d="M8 3.5v3M16 3.5v3" />
  </svg>
);

export const IconTarget = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <circle cx="12" cy="12" r="8.5" />
    <circle cx="12" cy="12" r="4.5" />
    <circle cx="12" cy="12" r="1" fill="currentColor" />
  </svg>
);

export const IconSpark = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M12 3.5 13.8 9l5.7 1.8-5.7 1.8L12 18.5l-1.8-5.9L4.5 10.8 10.2 9 12 3.5Z" />
  </svg>
);

export const IconChevronLeft = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="m14.5 5.5-6 6.5 6 6.5" />
  </svg>
);

export const IconChevronRight = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="m9.5 5.5 6 6.5-6 6.5" />
  </svg>
);

export const IconKeyboard = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <rect x="2.5" y="6" width="19" height="12" rx="2" />
    <path d="M6.5 10h.01M10 10h.01M13.5 10h.01M17 10h.01M8 14h8" />
  </svg>
);

export const IconTrash = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M4.5 6.5h15" />
    <path d="M9.5 6.5V4.5h5v2" />
    <path d="M6.5 6.5 7.5 20h9l1-13.5" />
  </svg>
);

export const IconEye = ({ className }: IconProps) => (
  <svg {...base} className={className}>
    <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);
