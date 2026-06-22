import { auth } from "./firebase";
import {
  EmailAuthProvider as RealEmailAuthProvider,
  onAuthStateChanged as realOnAuthStateChanged,
  reauthenticateWithCredential as realReauthenticateWithCredential,
  sendPasswordResetEmail as realSendPasswordResetEmail,
  signInWithEmailAndPassword as realSignInWithEmailAndPassword,
  signOut as realSignOut,
  updatePassword as realUpdatePassword,
} from "firebase/auth";

type FakeUser = {
  uid: string;
  email: string;
  displayName: string;
  emailVerified: boolean;
  getIdToken: () => Promise<string>;
};

type FakeAuth = {
  currentUser: FakeUser | null;
  __setCurrentUser: (user: FakeUser | null) => void;
};

type Credential = { email: string; password: string };

const useFakeFirebaseAuth = import.meta.env.DEV;
const storageKey = "salesanchor:e2e-firebase-auth-user";
const listeners = new Set<(user: FakeUser | null) => void>();

function getFakeAuth(): FakeAuth {
  return auth as unknown as FakeAuth;
}

function readStoredUser(): FakeUser | null {
  try {
    const seed = (window as unknown as { __salesanchorE2eAuthUser?: Partial<FakeUser> }).__salesanchorE2eAuthUser;
    if (seed && seed.uid && seed.email) {
      return {
        uid: seed.uid,
        email: seed.email,
        displayName: seed.displayName || seed.email,
        emailVerified: seed.emailVerified ?? true,
        getIdToken: async () => "e2e-fake-id-token",
      };
    }
    const raw = localStorage.getItem(storageKey);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<FakeUser>;
    if (!parsed.uid || !parsed.email) return null;
    return {
      uid: parsed.uid,
      email: parsed.email,
      displayName: parsed.displayName || parsed.email,
      emailVerified: parsed.emailVerified ?? true,
      getIdToken: async () => "e2e-fake-id-token",
    };
  } catch {
    return null;
  }
}

function writeStoredUser(user: FakeUser | null): void {
  try {
    (window as unknown as { __salesanchorE2eAuthUser?: unknown }).__salesanchorE2eAuthUser = user
      ? {
          uid: user.uid,
          email: user.email,
          displayName: user.displayName,
          emailVerified: user.emailVerified,
        }
      : undefined;
    if (!user) {
      localStorage.removeItem(storageKey);
      return;
    }
    localStorage.setItem(
      storageKey,
      JSON.stringify({
        uid: user.uid,
        email: user.email,
        displayName: user.displayName,
        emailVerified: user.emailVerified,
      }),
    );
  } catch {
    // ignore
  }
}

let fakeCurrentUser: FakeUser | null = readStoredUser();

function syncFakeAuth(): void {
  const fakeAuth = getFakeAuth();
  fakeAuth.__setCurrentUser(fakeCurrentUser);
  writeStoredUser(fakeCurrentUser);
  for (const listener of listeners) listener(fakeCurrentUser);
}

function makeUser(email: string): FakeUser {
  const localPart = email.split("@")[0] || "e2e-user";
  return {
    uid: `e2e-${localPart}`,
    email,
    displayName: email,
    emailVerified: true,
    getIdToken: async () => "e2e-fake-id-token",
  };
}

export function getAuth() {
  return auth;
}

export function onAuthStateChanged(
  _auth: unknown,
  callback: (user: FakeUser | null) => void,
): () => void {
  if (!useFakeFirebaseAuth) {
    return realOnAuthStateChanged(_auth as never, callback as never);
  }
  listeners.add(callback);
  queueMicrotask(() => callback(fakeCurrentUser));
  return () => {
    listeners.delete(callback);
  };
}

export async function signInWithEmailAndPassword(
  _auth: unknown,
  email: string,
  password: string,
): Promise<{ user: FakeUser }> {
  if (!useFakeFirebaseAuth) {
    return realSignInWithEmailAndPassword(_auth as never, email, password) as never;
  }
  fakeCurrentUser = makeUser(email);
  syncFakeAuth();
  return { user: fakeCurrentUser };
}

export async function signOut(_auth: unknown): Promise<void> {
  if (!useFakeFirebaseAuth) {
    await realSignOut(_auth as never);
    return;
  }
  fakeCurrentUser = null;
  syncFakeAuth();
}

export async function sendPasswordResetEmail(
  _auth: unknown,
  email: string,
): Promise<void> {
  if (!useFakeFirebaseAuth) {
    await realSendPasswordResetEmail(_auth as never, email);
    return;
  }
}

export const EmailAuthProvider = useFakeFirebaseAuth
  ? {
      credential(email: string, password: string): Credential {
        return { email, password };
      },
    }
  : RealEmailAuthProvider;

export async function reauthenticateWithCredential(
  user: FakeUser,
  credential: Credential,
): Promise<{ user: FakeUser }> {
  if (!useFakeFirebaseAuth) {
    return realReauthenticateWithCredential(user as never, credential as never) as never;
  }
  if (user.email !== credential.email) {
    throw new Error("auth/user-mismatch");
  }
  return { user };
}

export async function updatePassword(
  _user: FakeUser,
  _newPassword: string,
): Promise<void> {
  if (!useFakeFirebaseAuth) {
    await realUpdatePassword(_user as never, _newPassword);
  }
}
