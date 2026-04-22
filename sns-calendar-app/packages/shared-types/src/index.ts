export const VERSION = "0.1.0";

export const SNS_ACCOUNT_PLATFORMS = ["x", "ig"] as const;
export type SnsAccountPlatform = (typeof SNS_ACCOUNT_PLATFORMS)[number];
