import type { Config } from "tailwindcss";
import sharedConfig from "@sns-calendar/config/tailwind";

const config: Config = {
  presets: [sharedConfig],
  content: [
    "./src/**/*.{ts,tsx}",
    "../../packages/ui/src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        x: "#000000",
        ig: "#E4405F",
      },
    },
  },
};

export default config;

