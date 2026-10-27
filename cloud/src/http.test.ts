import { describe, expect, it } from "vitest";

import { bearerMatches, byteRange, passwordMatches, sessionCookie, sessionValid, sessionValue } from "./http";

const withCookie = (value: string) => new Request("https://x/api/library", { headers: { Cookie: `other=1; lights_session=${value}` } });

describe("session cookie", () => {
  it("accepts its own cookie", async () => {
    expect(await sessionValid(withCookie(await sessionValue("pw")), "pw")).toBe(true);
  });

  it("rejects a cookie signed with another password, an expired one, or none", async () => {
    expect(await sessionValid(withCookie(await sessionValue("old")), "pw")).toBe(false);
    expect(await sessionValid(withCookie(await sessionValue("pw", Date.now() - 1)), "pw")).toBe(false);
    expect(await sessionValid(new Request("https://x/"), "pw")).toBe(false);
    expect(await sessionValid(withCookie(await sessionValue("pw")), undefined)).toBe(false);
  });

  it("is HttpOnly, and Secure except on plain http", () => {
    expect(sessionCookie("v", true)).toContain("HttpOnly; SameSite=Lax; Secure");
    expect(sessionCookie("v", false)).not.toContain("Secure");
  });
});

describe("passwords and tokens", () => {
  it("needs the exact password, and a password to be set", () => {
    expect(passwordMatches("pw", "pw")).toBe(true);
    expect(passwordMatches("pw ", "pw")).toBe(false);
    expect(passwordMatches(undefined, "pw")).toBe(false);
    expect(passwordMatches("", undefined)).toBe(false);
  });

  it("checks the device's bearer token", () => {
    const request = new Request("https://x/device", { headers: { Authorization: "Bearer tok" } });
    expect(bearerMatches(request, "tok")).toBe(true);
    expect(bearerMatches(request, "other")).toBe(false);
    expect(bearerMatches(request, undefined)).toBe(false);
  });
});

describe("byteRange", () => {
  it("reads the forms browsers send", () => {
    expect(byteRange("bytes=0-", 100)).toEqual([0, 99]);
    expect(byteRange("bytes=10-19", 100)).toEqual([10, 19]);
    expect(byteRange("bytes=90-500", 100)).toEqual([90, 99]);
    expect(byteRange("bytes=-10", 100)).toEqual([90, 99]);
  });

  it("serves the whole file for no header or ones it doesn't handle", () => {
    expect(byteRange(null, 100)).toBeNull();
    expect(byteRange("bytes=0-1,5-6", 100)).toBeNull();
    expect(byteRange("bytes=-", 100)).toBeNull();
  });

  it("says when a range is past the end", () => {
    expect(byteRange("bytes=100-", 100)).toBe("unsatisfiable");
    expect(byteRange("bytes=5-2", 100)).toBe("unsatisfiable");
    expect(byteRange("bytes=-0", 100)).toBe("unsatisfiable");
  });
});
