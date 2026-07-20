/**
 * AuthService — expect-auth/1.0
 * PredictionBundle 契約とは独立。
 */

export type AuthSchemaVersion = "expect-auth/1.0";
export type FavoritesSchemaVersion = "expect-favorites/1.0";

export interface AuthUser {
  id: string;
  display_name?: string | null;
}

export interface FavoriteItem {
  race_id: string;
  place?: string | null;
  name?: string | null;
  badge?: string | null;
  post_time?: string | null;
  date_label?: string | null;
  added_at?: number | null;
}

/** サーバー同期用お気に入り状態（最大3件） */
export interface FavoritesState {
  schema_version?: FavoritesSchemaVersion;
  race_ids: string[];
  items: FavoriteItem[];
  synced_at?: string | null;
}

export interface AuthLoginRequest {
  id: string;
  password?: string | null;
  /** ログイン時に localStorage 分を送ってサーバーへマージ可能 */
  favorites?: FavoritesState;
}

export interface AuthLoginResponse {
  schema_version: AuthSchemaVersion;
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
  favorites?: FavoritesState;
}

export interface AuthMeResponse {
  schema_version: AuthSchemaVersion;
  user: AuthUser;
  favorites?: FavoritesState;
}

export interface AuthLogoutResponse {
  schema_version: AuthSchemaVersion;
  logged_out: true;
}

export interface AuthFavoritesResponse {
  schema_version: AuthSchemaVersion;
  favorites: FavoritesState;
}

/** Phase9 — 一時ID開始 */
export interface AuthInviteStartRequest {
  invite_id: string;
}

export interface AuthInviteStartResponse {
  schema_version: AuthSchemaVersion;
  invite_id: string;
  setup_token: string;
  token_type: "bearer";
  expires_in: number;
  next: "setup";
}

/** Phase9 — 初回設定（成功時 data は AuthLoginResponse） */
export interface AuthSetupRequest {
  setup_token?: string;
  login_id: string;
  password: string;
  terms_accepted: boolean;
  favorites?: FavoritesState;
}

export type InviteStatus = "issued" | "activated" | "disabled" | "expired";

export interface InvitationRecord {
  invite_id: string;
  status: InviteStatus;
  issued_at?: string | null;
  expires_at?: string | null;
  activated_at?: string | null;
  activated_user_id?: string | null;
  note?: string | null;
}

export interface UserRecord {
  user_id: string;
  password_hash: string;
  display_name?: string | null;
  invite_id?: string | null;
  status: "active" | "disabled";
  created_at?: string | null;
  terms_version?: string | null;
  terms_accepted_at?: string | null;
}
