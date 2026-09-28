with open('frontend/src/pages/Onboard.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace inline dark greens with light orange/white theme
text = text.replace('linear-gradient(160deg, #042f22 0%, #0a7a52 40%, #0d9668 100%)', 'linear-gradient(160deg, #ffffff 0%, #fff7ed 40%, #ffedd5 100%)')
text = text.replace('rgba(45,212,184,0.4)', 'rgba(251,146,60,0.15)') # floating orb
text = text.replace('border-brand-900', 'border-brand-200')

# Replace text colors on the light background
text = text.replace('text-white/90', 'text-slate-800')
text = text.replace('text-white/80', 'text-slate-700')
text = text.replace('text-white/60', 'text-slate-500')
text = text.replace('text-white/40', 'text-slate-400')
text = text.replace('text-brand-50/80', 'text-brand-900/80')
text = text.replace('text-brand-100', 'text-brand-800')
text = text.replace('text-brand-200', 'text-brand-700')
text = text.replace('text-brand-300', 'text-brand-600')

# Specific text-white replacements in the hero section and titles
text = text.replace('className="text-white', 'className="text-slate-900')
text = text.replace('text-white mb-2', 'text-slate-900 mb-2')
text = text.replace('text-3xl font-display font-bold text-white', 'text-3xl font-display font-bold text-slate-900')
text = text.replace('text-5xl font-display font-extrabold text-white', 'text-5xl font-display font-extrabold text-slate-900')
text = text.replace('text-sm font-semibold text-white/90', 'text-sm font-semibold text-slate-800')
text = text.replace('text-white text-xl', 'text-slate-900 text-xl')
text = text.replace('text-white/70', 'text-slate-600')

# Glass cards background (from dark glass to light glass)
text = text.replace('bg-white/4', 'bg-white/60 backdrop-blur-3xl')
text = text.replace('bg-white/5', 'bg-white/50 backdrop-blur-3xl')
text = text.replace('bg-white/10', 'bg-white/80')
text = text.replace('border-white/8', 'border-white border-slate-200/60 shadow-xl')
text = text.replace('border-white/10', 'border-white border-slate-200/60 shadow-xl')

with open('frontend/src/pages/Onboard.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
