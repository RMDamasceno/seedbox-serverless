export interface ILoginRequest {
  password: string;
}

export interface ILoginResponse {
  token: string;
  expiresAt: string;
}
