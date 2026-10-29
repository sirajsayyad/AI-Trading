const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const ts = require("typescript");

test("simultaneous expired-token requests share one refresh and preserve multipart bodies", async () => {
  const storage = new Map([["access_token", "expired"], ["refresh_token", "original-refresh"]]);
  let refreshes = 0;
  let multipart = false;
  const moduleObject = { exports: {} };
  const source = fs.readFileSync(require.resolve("../src/lib/api.ts"), "utf8");
  const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } });
  vm.runInNewContext(outputText, {
    module: moduleObject, exports: moduleObject.exports,
    require(name) { assert.equal(name, "./dashboard-cache"); return { clearDashboardCache() {} }; },
    process: { env: {} }, window: { location: { origin: "http://localhost" } },
    localStorage: { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) },
    AbortSignal, FormData, URL,
    async fetch(url, options) {
      if (url === "/api/auth/refresh") {
        refreshes++;
        await new Promise(resolve => setTimeout(resolve, 15));
        return new Response(JSON.stringify({ access_token: "fresh", refresh_token: "rotated-refresh" }));
      }
      if (options.headers.Authorization !== "Bearer fresh") return new Response('{"detail":"Expired"}', { status: 401 });
      if (url === "/api/data/upload") {
        multipart = options.body instanceof FormData && !("Content-Type" in options.headers);
      }
      return new Response('{"ok":true}');
    },
  });
  const client = moduleObject.exports;
  const results = await Promise.all([client.request("/courses"), client.request("/auth/me")]);
  assert(results.every(result => result.ok));
  assert.equal(refreshes, 1);
  const body = new FormData(); body.append("file", new Blob(["test"]), "fixture.csv");
  await client.request("/data/upload", { method: "POST", body });
  assert(multipart);
});
