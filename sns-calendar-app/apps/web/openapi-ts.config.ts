import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: "../api/openapi.json",
  output: "src/generated",
  plugins: ["@hey-api/client-fetch"],
});

