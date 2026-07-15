// src/theme.js — CBC Grading design tokens

export const colors = {
  // Backgrounds
  bgDeep: "#0D0F1A",
  bgCard: "#0a0c18",
  bgElevated: "#12152a",
  bgBorder: "#1a1d2e",

  // Brand
  brandPurple: "#7B5EA7",
  brandTeal: "#00C9A7",
  gold: "#FFD700",

  // Text
  textPrimary: "#FFFFFF",
  textSecondary: "#888899",
  textMuted: "#444455",

  // Grades
  gradeGold: "#FFD700",
  gradeSilver: "#C0C0C0",
  gradeBronze: "#CD7F32",
  gradeBlue: "#4A90D9",
  gradeGray: "#888888",
};

export const typography = {
  display: "Rajdhani_700Bold",
  displayMedium: "Rajdhani_500Medium",
  body: "Inter_400Regular",
  bodyMedium: "Inter_500Medium",
  bodySemiBold: "Inter_600SemiBold",
};

export const GRADE_CONFIG = {
  10: { color: "#FFD700",  textColor: "#7A5B00", label: "GEM MINT" },
  9:  { color: "#C0C0C0",  textColor: "#3A3A3A", label: "MINT" },
  8:  { color: "#CD7F32",  textColor: "#FFFFFF", label: "NEAR MINT" },
  7:  { color: "#4A90D9",  textColor: "#FFFFFF", label: "EXCELLENT" },
  6:  { color: "#888888",  textColor: "#FFFFFF", label: "GOOD" },
};
