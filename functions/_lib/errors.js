export function jsonOk(data, meta = {}, init = {}) {
  const body = {
    ok: true,
    meta: {
      generated_at: new Date().toISOString(),
      source: meta.source || "mock",
      cache: meta.cache || "miss",
      ...meta,
    },
    data,
  };
  return new Response(JSON.stringify(body), {
    status: init.status || 200,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": init.cacheControl || "public, max-age=30",
      ...(init.headers || {}),
    },
  });
}

export function jsonError(code, message, status = 400, details = null) {
  return new Response(
    JSON.stringify({
      ok: false,
      error: { code, message, details },
    }),
    {
      status,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store",
      },
    }
  );
}
