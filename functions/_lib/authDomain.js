/** AuthService DTO 組み立て（expect-auth/1.0） */

export const AUTH_SCHEMA = "expect-auth/1.0";

export function toLoginResponse(token, expiresIn, user, favorites) {
  return {
    schema_version: AUTH_SCHEMA,
    access_token: token,
    token_type: "bearer",
    expires_in: expiresIn,
    user: {
      id: user.id,
      display_name: user.display_name != null ? user.display_name : user.id,
    },
    favorites: favorites || undefined,
  };
}

export function toMeResponse(user, favorites) {
  return {
    schema_version: AUTH_SCHEMA,
    user: {
      id: user.id,
      display_name: user.display_name != null ? user.display_name : user.id,
    },
    favorites: favorites || undefined,
  };
}

export function toLogoutResponse() {
  return {
    schema_version: AUTH_SCHEMA,
    logged_out: true,
  };
}

export function toFavoritesResponse(favorites) {
  return {
    schema_version: AUTH_SCHEMA,
    favorites,
  };
}
