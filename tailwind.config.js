tailwind.config = {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand:       "#00B2E3",
        "brand-dim": "#0099C7",
        "brand-dark":"#002855",
        "brand-bg":  "#E0F7FB",
        "brand-bg2": "#B3E5FC",
        "surface":   "#FFFFFF",
        "bg-main":   "#F8FAFC",
        "text-main": "#1E293B",
        "text-muted":"#64748B",
        "border-subtle": "rgba(0,0,0,0.06)",
        success:     "#059669",
        "success-bg":"#D1FAE5",
        danger:      "#DC2626",
        "danger-bg": "#FEE2E2",
      },
      fontFamily: {
        sans: ["Hanken Grotesk","system-ui","sans-serif"],
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.25rem",
        "4xl": "1.5rem",
        full: "9999px",
      },
    }
  }
}
