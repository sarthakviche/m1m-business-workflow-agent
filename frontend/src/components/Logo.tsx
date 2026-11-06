// The one place the Munim.ai logo is defined. The images come from docs/assets/banner.png
// and need a white or cream background: the orange mark disappears on solid orange.

import markUrl from '../assets/brand/munim-mark.png'
import wordmarkUrl from '../assets/brand/munim-wordmark.png'

const SIZES = {
  md: { mark: 'h-9', word: 'h-[22px]', gap: 'gap-2' },
  lg: { mark: 'h-11', word: 'h-[27px]', gap: 'gap-2.5' },
}

/** The mark on its own. Decorative by default, since text usually sits beside it. */
export function LogoMark({ className = '', label }: { className?: string; label?: string }) {
  return <img src={markUrl} alt={label ?? ''} draggable={false} className={`w-auto select-none ${className}`} />
}

/** The full logo: mark and wordmark. */
export default function Logo({ size = 'md' }: { size?: keyof typeof SIZES }) {
  const s = SIZES[size]
  return (
    <span role="img" aria-label="Munim.ai" className={`inline-flex items-center ${s.gap}`}>
      <LogoMark className={s.mark} />
      <img src={wordmarkUrl} alt="" draggable={false} className={`w-auto select-none ${s.word}`} />
    </span>
  )
}
