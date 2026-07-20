import { getBearer, verifyStubToken } from "../../_lib/auth.js";
import { toMeResponse } from "../../_lib/authDomain.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { UserRepository } from "../../_lib/userRepository.js";
import { getUserState } from "../../_lib/userStore.js";

/** AuthService — GET /api/auth/me */
export async function onRequestGet(context) {
  const token = getBearer(context.request);
  const session = verifyStubToken(token, { purpose: "access" });
  if (!session) {
    return jsonError("UNAUTHORIZED", "login required", 401);
  }

  const profile = await UserRepository.get(context, session.id);
  const display_name = profile
    ? profile.display_name
    : String(session.id).replace(/^invite:/, "");

  const state = getUserState(session.id);
  return jsonOk(
    toMeResponse(
      {
        id: session.id,
        display_name,
        role: profile && profile.role ? profile.role : session.role || "USER",
      },
      state.favorites
    ),
    {
      source: "stub-auth",
      service: "AuthService",
      contract: "AuthMeResponse",
      cache: "bypass",
    },
    { cacheControl: "no-store" }
  );
}
