// Tailwind for the MyRoomSearch page. tools/build_page.py compiles it and bakes the CSS into the page,
// because the site allows no outside scripts or stylesheets (see docs/_headers).
// The "tw-" prefix keeps Tailwind's classes apart from the page's own, and preflight is off so
// Tailwind doesn't reset the parts of the page that aren't built with it.
module.exports = {
  prefix: "tw-",
  content: ["./page/results.html"],
  corePlugins: { preflight: false },
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: "#0f2a3a", 2: "#3d5566", 3: "#688090" },
        line: "#d6e2e7",
        mist: "#f2f7f8",
        ocean: { DEFAULT: "#0a6e7d", dark: "#085966", deep: "#0b3a4e", soft: "#e1f0f4" },
        reef: { DEFAULT: "#2bb8ad", soft: "#ddf3ef", ink: "#11615b" },
        sun: { DEFAULT: "#ffc53d", soft: "#fff4d4", ink: "#7a5300", hover: "#ffb703" },
      },
      fontFamily: {
        sans: ['"DM Sans"', "system-ui", "-apple-system", '"Segoe UI"', "sans-serif"],
        serif: ["Fraunces", "Georgia", '"Times New Roman"', "serif"],
      },
      boxShadow: { card: "0 1px 2px rgb(15 42 58 / 0.06), 0 12px 30px -14px rgb(15 42 58 / 0.25)" },
    },
  },
};
