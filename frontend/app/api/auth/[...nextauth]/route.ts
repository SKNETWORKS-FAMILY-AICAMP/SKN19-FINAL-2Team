import NextAuth from "next-auth";
import KakaoProvider from "next-auth/providers/kakao";
import CredentialsProvider from "next-auth/providers/credentials";

const BACKEND_URL =
  process.env.BACKEND_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://backend:8000";

const handler = NextAuth({
  providers: [
    KakaoProvider({
      clientId: process.env.KAKAO_CLIENT_ID!,
      clientSecret: process.env.KAKAO_CLIENT_SECRET!,
    }),

    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        const response = await fetch(`${BACKEND_URL}/users/login/local`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: credentials.email,
            password: credentials.password,
          }),
        });

        if (!response.ok) return null;
        const data = await response.json();

        if (data?.withdraw_pending && data?.member_id) {
          throw new Error(`WITHDRAW_PENDING:${data.member_id}`);
        }

        return {
          id: data.member_id,
          name: data.nickname ?? credentials.email.split("@")[0],
          email: data.email ?? credentials.email,
          roleType: data.role_type ?? "USER",
          userMode: data.user_mode ?? "BEGINNER",
        };
      },
    }),
  ],
  session: { strategy: "jwt" },

  callbacks: {
    async signIn({ user, account }) {
      if (account?.provider === "kakao") {
        try {
          console.log("[NextAuth] Sending Kakao login request to Backend...");
          const response = await fetch(`${BACKEND_URL}/users/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              kakao_id: account.providerAccountId,
              nickname: user.name,
              email: user.email,
              profile_image: user.image,
            }),
          });

          if (!response.ok) {
            console.error(`[NextAuth] Backend Login Failed. Status: ${response.status}`);
            return true; // Allow login but as guest-like state (fallback)
          }

          const data = await response.json();
          console.log("[NextAuth] Backend Response:", data);

          if (data?.withdraw_pending && data?.member_id) {
            return `/recover?memberId=${data.member_id}`;
          }

          if (data?.link_available && data?.existing_member_id) {
            const params = new URLSearchParams({
              email: user.email || "",
              kakao_id: account.providerAccountId,
              kakao_nickname: user.name || "",
              kakao_profile_image: user.image || "",
              existing_member_id: String(data.existing_member_id),
            });
            return `/link-account?${params.toString()}`;
          }

          // [Fix] Ensure ID is string to match NextAuth types
          user.id = String(data.member_id);
          (user as any).roleType = data.role_type || "USER";
          (user as any).userMode = data.user_mode || "BEGINNER";
          return true;
        } catch (error) {
          console.error("[NextAuth] SignIn Error:", error);
          if (account?.providerAccountId) {
            user.id = String(account.providerAccountId);
          }
          return true;
        }
      }
      return true;
    },

    async jwt({ token, user }) {
      if (user) {
        console.log("[NextAuth] JWT Callback - User Logged In:", { id: user.id });
        token.id = (user as any).id;
        token.roleType = (user as any).roleType || "USER";
        token.userMode = (user as any).userMode || "BEGINNER";
      }
      return token;
    },

    async session({ session, token }) {
      console.log("[NextAuth] Session Callback Triggered:", { tokenId: token.id });
      if (session.user) {
        session.user.id = token.id as string;
        (session.user as any).roleType = token.roleType as string;
        (session.user as any).userMode = token.userMode as string;
      }
      return session;
    },
  },
});

export { handler as GET, handler as POST };
