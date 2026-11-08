import type { ReactNode } from 'react'

interface IconProps {
  size?: number
  className?: string
}

const base = (children: ReactNode) =>
  function Icon({ size = 20, className }: IconProps) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.8}
        strokeLinecap="round"
        strokeLinejoin="round"
        className={className}
        aria-hidden="true"
      >
        {children}
      </svg>
    )
  }

export const IconThermometer = base(<path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z" />)
export const IconCloudRain = base(
  <>
    <path d="M4 14.9A7 7 0 1 1 15.7 8h1.8a4.5 4.5 0 0 1 2.5 8.2" />
    <path d="M16 14v6M8 14v6M12 16v6" />
  </>,
)
export const IconDroplets = base(
  <>
    <path d="M7 16.3c2.2 0 4-1.83 4-4.05 0-1.16-.57-2.26-1.71-3.19S7.29 6.75 7 5.3c-.29 1.45-1.14 2.84-2.29 3.76S3 11.1 3 12.25c0 2.22 1.8 4.05 4 4.05z" />
    <path d="M12.56 6.6A10.97 10.97 0 0 0 14 3.02c.5 2.5 2 4.9 4 6.5s3 3.5 3 5.5a6.98 6.98 0 0 1-11.91 4.97" />
  </>,
)
export const IconDatabase = base(
  <>
    <ellipse cx="12" cy="5" rx="9" ry="3" />
    <path d="M3 5v14a9 3 0 0 0 18 0V5" />
    <path d="M3 12a9 3 0 0 0 18 0" />
  </>,
)
export const IconWaves = base(
  <>
    <path d="M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1" />
    <path d="M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1" />
    <path d="M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1" />
  </>,
)
export const IconSearch = base(
  <>
    <circle cx="11" cy="11" r="8" />
    <path d="m21 21-4.3-4.3" />
  </>,
)
export const IconX = base(<path d="M18 6 6 18M6 6l12 12" />)
export const IconSliders = base(
  <>
    <path d="M21 4h-7M10 4H3M21 12h-9M8 12H3M21 20h-5M12 20H3M14 2v4M8 10v4M16 18v4" />
  </>,
)
export const IconReset = base(
  <>
    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
    <path d="M3 3v5h5" />
  </>,
)
export const IconDownload = base(
  <>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <path d="m7 10 5 5 5-5M12 15V3" />
  </>,
)
export const IconInfo = base(
  <>
    <circle cx="12" cy="12" r="10" />
    <path d="M12 16v-4M12 8h.01" />
  </>,
)
export const IconChevronDown = base(<path d="m6 9 6 6 6-6" />)
export const IconCompare = base(
  <>
    <circle cx="18" cy="18" r="3" />
    <circle cx="6" cy="6" r="3" />
    <path d="M13 6h3a2 2 0 0 1 2 2v7M11 18H8a2 2 0 0 1-2-2V9" />
  </>,
)
export const IconPlus = base(<path d="M5 12h14M12 5v14" />)
export const IconMinus = base(<path d="M5 12h14" />)

export function Logo({ size = 46 }: { size?: number }) {
  return (
    <svg viewBox="0 0 32 32" width={size} height={size} aria-hidden="true" className="logo">
      <circle cx="16" cy="16" r="14" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M4 18c4-3 8 3 12 0s8-3 12 0" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M6 11c3-2 6 2 10 0s7-2 10 0" fill="none" stroke="currentColor" strokeWidth="1.5" opacity=".5" />
    </svg>
  )
}
